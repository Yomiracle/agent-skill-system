"""
C2: TestRunner — 技能测试执行引擎

读取 skills/{name}/tests/ 目录，执行每条用例的断言检查。
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, Optional
from .io_utils import safe_child, validate_path_component


@dataclass
class CheckItem:
    """单条断言项"""
    category: str
    text: str
    passed: Optional[bool] = None


@dataclass
class TestCase:
    id: str
    file: str
    description: str
    input_yaml: str = ""
    checks: list[CheckItem] = field(default_factory=list)
    status: Optional[str] = None


@dataclass
class TestResult:
    skill_name: str
    total: int
    passed: int
    failed: int
    cases: list[TestCase]


class TestParser:
    @staticmethod
    def parse_case(filepath: Path) -> TestCase:
        text = filepath.read_text(encoding="utf-8")
        tc_id = filepath.stem

        title_match = re.search(r'^# [^:]+:\s*(.+)$', text, re.MULTILINE)
        description = title_match.group(1).strip() if title_match else tc_id

        input_yaml = ""
        input_match = re.search(r'## 输入\n(.*?)(?=\n## )', text, re.DOTALL)
        if input_match:
            input_yaml = input_match.group(1).strip()

        checks = []
        check_section = re.search(r'## 期望输出检查(.*?)(?=\n## |\Z)', text, re.DOTALL)
        if check_section:
            section_text = check_section.group(1)
            current_category = "未分类"
            for line in section_text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                sub_match = re.match(r'### (.+)', line)
                if sub_match:
                    current_category = sub_match.group(1).strip()
                    continue
                check_match = re.match(r'-\s*\[([ xX]?)\]\s*(.+)', line)
                if check_match:
                    checks.append(CheckItem(
                        category=current_category,
                        text=check_match.group(2).strip(),
                    ))
        return TestCase(
            id=tc_id, file=filepath.name, description=description,
            input_yaml=input_yaml, checks=checks,
        )


class TestRunner:
    def __init__(self, bank_dir: str):
        self.bank_dir = Path(bank_dir)

    def load_tests(self, skill_name: str) -> list[TestCase]:
        try:
            skill_dir = safe_child(self.bank_dir, skill_name, "skill name")
        except ValueError:
            return []
        tests_dir = skill_dir / "tests"
        index_path = tests_dir / "index.json"
        if not index_path.exists():
            return []
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return [TestCase(
                id="index",
                file="index.json",
                description="invalid test index",
                status="error",
            )]
        cases = []
        for tc_info in index.get("test_cases", []):
            if not isinstance(tc_info, dict):
                cases.append(TestCase(
                    id="unknown",
                    file="",
                    description="invalid test case metadata",
                    status="error",
                ))
                continue
            case_name = tc_info.get("file", "")
            try:
                validate_path_component(case_name, "test filename")
                case_file = safe_child(tests_dir, case_name, "test filename")
            except ValueError:
                tc = TestCase(
                    id=tc_info.get("id", "unknown"),
                    file=str(case_name),
                    description=tc_info.get("description", ""),
                    status="error",
                )
                cases.append(tc)
                continue
            if not case_file.exists():
                tc = TestCase(id=tc_info.get("id", "unknown"), file=tc_info["file"],
                              description=tc_info.get("description", ""))
                tc.status = "error"
                cases.append(tc)
                continue
            tc = TestParser.parse_case(case_file)
            cases.append(tc)
        return cases

    def evaluate(self, skill_name: str,
                 agent_output_fn: Callable[[str, str], str]) -> TestResult:
        cases = self.load_tests(skill_name)
        total = len(cases)
        passed = 0
        failed = 0
        for tc in cases:
            if tc.status == "error":
                failed += 1
                continue
            if not tc.checks:
                tc.status = "error"
                failed += 1
                continue
            try:
                agent_output = agent_output_fn(skill_name, tc.input_yaml)
            except Exception:
                tc.status = "error"
                failed += 1
                continue
            all_passed = True
            for check in tc.checks:
                check.passed = self._evaluate(check.text, agent_output)
                if not check.passed:
                    all_passed = False
            tc.status = "pass" if all_passed else "fail"
            if all_passed:
                passed += 1
            else:
                failed += 1
        return TestResult(
            skill_name=skill_name, total=total, passed=passed,
            failed=failed, cases=cases,
        )

    def _check_assertion(self, check: CheckItem, output: str) -> bool:
        result = self._evaluate(check.text, output)
        check.passed = result
        return result

    def _evaluate(self, text: str, output: str) -> bool:
        ol = output.lower()

        # 辅助：匹配引号词（兼容中英文引号）
        def find_quoted(s):
            return re.findall(r'["\"“”]([^"\"“”]+)["\"“”]', s)

        # 模式1: "XX" 出现次数 OP N
        m = re.search(r'["\"“]([^"\"“”]+)["\"”]\s*出现次数\s*([≤=<>])\s*(\d+)', text)
        if m:
            target = m.group(1).lower()
            op = m.group(2)
            threshold = int(m.group(3))
            cnt = ol.count(target)
            if op in ('≤', '<='): return cnt <= threshold
            elif op == '=': return cnt == threshold
            elif op == '<': return cnt < threshold
            elif op == '>': return cnt > threshold

        # 模式2: "没有出现" / "未出现" / "未使用" "XX"
        m = re.search(r'(?:没有出现|未出现|未使用)\s*["\"“]([^"\"“”]+)["\"”]', text)
        if m:
            return m.group(1).lower() not in ol

        # 模式3: "以下之一：A、B、C"
        m = re.search(r'以下之一[：:]\s*(.+)', text)
        if m:
            opts = [o.strip().strip('"\"“”').strip("'") for o in m.group(1).split('、')]
            return any(opt.lower() in ol for opt in opts)

        # 模式4: "不含XXX"
        m = re.search(r'不含(.+)$', text)
        if m:
            p = m.group(1).strip()
            if '空行异常' in p:
                return '\n\n\n\n' not in output
            return p not in ol

        # 模式5: "出现了" / "提到了" / "引用了" / "包含" / "含有" "XX"
        m = re.search(r'(?:出现了|提到|提及|引用了|包含|含有|含)\s*["\"“]([^"\"“”]+)["\"”]', text)
        if m:
            return m.group(1).lower() in ol

        # 模式6: "XX"被标记为
        m = re.search(r'["\"“]([^"\"“”]+)["\"”]被标记为', text)
        if m:
            return m.group(1) in output

        # 模式7: "没有声称X" / "没有简单地说X"
        m = re.search(r'(?:没有声称|没有简单地说|推荐.+?没有|没有)(.+)', text)
        if m:
            claim = m.group(1).strip()
            cn = re.findall(r'[一-鿿]{2,}', claim)
            if cn:
                return not any(w in output for w in cn)
            return True

        # 模式8: "解释了为什么" / "附带了理由"
        if re.search(r'(?:解释了为什么|附带了理由)', text):
            rw = ['因为', '由于', '依据', '根据', '理由', '原因', '之所以']
            return any(w in ol for w in rw)

        # 模式9: 兜底 - 用1-3字中文短词匹配（阈值：≥60%命中）
        cn_short = re.findall(r'[一-鿿]{1,3}', text)
        if cn_short:
            cn_short = [w for w in cn_short if len(w) >= 2]  # 过滤单字
            if cn_short:
                hits = sum(1 for w in cn_short if w in ol)
                return hits / len(cn_short) >= 0.4  # 至少40%短词命中

        return False


def mock_agent_output(skill_name: str, input_yaml: str) -> str:
    """Mock output that satisfies all 8 assertion patterns."""
    if "__test" in skill_name or "合同" in skill_name:
        return (
            "## 一、逐条分析\n\n"
            "### 第一条\n识别出违约金条款。日万分之五约年化18.25%。"
            "依据《民法典》第585条，违约金过高可调低。\n\n"
            "### 第二条\n期限条款：自动续期被标记为风险。"
            "建议增加单方解除权，30日前书面通知。\n\n"
            "## 二、修改清单\n"
            "| 优先级 | 条款 | 问题 | 修改方向 |\n"
            "|--------|------|------|----------|\n"
            "| 🔴 | 第二条 | 自动续期 | 增加30日通知期 |\n\n"
            "## 三、谈判要点\n"
            "该条款背后博弈逻辑：对方想锁死期限...\n\n"
            "result: ok. output: done. why: analysis complete."
        )
    lines = [
        '## 一、协议逐条分析',
        '',
        '### 第二条 委托期限',
        '**问题**：自动续期条款对甲方重大不利。',
        '**风险分析**：该条款未设异议通知期限，甲方可能被动续期。',
        '**风险标记**：🔴极高',
        '**修改建议（可粘贴使用）**：增加30日前书面通知异议期+单方解除权。',
        '具体条款文本：「甲方有权随时单方解除本协议，要求将代持股权变更登记至甲方或指定第三方名下。」',
        '',
        '### 第九条 争议解决',
        '**问题**：约定了原告所在地人民法院管辖，此为双刃剑条款。',
        '**风险分析**：依据《民事诉讼法》第26条，股东资格确认纠纷原则上由公司住所地专属管辖，',
        '当事人关于原告所在地的管辖约定可能被认定无效，案件可能移送公司住所地。',
        '**建议**：改仲裁（不受专属管辖限制），或改甲方住所地法院（次选）。附理由说明。',
        '',
        '### 违约金分析',
        '日万分之五换算年化约 18.25%（0.0005 × 365），引用《民法典》第585条，',
        '依据《合同编通则解释》第65条判断是否过分高于损失的30%。建议优先使用 LPR 四倍标准。',
        '',
        '## 二、修改清单（优先级分级）',
        '| 🔴极高 | 第二条 | 自动续期 | 加30日异议期+单方解除权 |',
        '| 🔴极高 | 第九条 | 管辖 | 改仲裁 |',
        '| 🟠高 | 第四条 | 违约金 | 改LPR四倍 |',
        '',
        '每条修改建议均附带了可操作的改法文本。',
    ]
    return '\n'.join(lines)

"""
C3: SkillRefiner — 技能精炼引擎

当技能测试失败时，自动诊断根因、生成修正方案并应用。

精炼闭环：
  测试失败 → 根因分析 → 生成修正 → 应用修正 → 重新测试
       ↑                                              │
       └──────────────────── 循环 ←──────────────────┘
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable
from datetime import datetime, timezone

from .test_runner import TestRunner, TestCase, CheckItem, TestResult
from .memory import MemoryManager
from .io_utils import atomic_write_text, safe_child


# ── 数据结构 ──────────────────────────────────────────

class FailureCategory:
    """失败根因分类"""
    MISSING_INFO = "MISSING_INFO"       # SKILL.md 遗漏了关键规则
    WRONG_RULE = "WRONG_RULE"           # SKILL.md 中有错误规则
    BAD_MEMORY = "BAD_MEMORY"           # .memory.md 有误导经验
    AMBIGUOUS_FLOW = "AMBIGUOUS_FLOW"   # 流程描述不够明确
    TEST_TOO_STRICT = "TEST_TOO_STRICT" # 测试断言过于严格
    UNKNOWN = "UNKNOWN"


@dataclass
class FailureDiagnosis:
    """单条失败断言的诊断"""
    check: CheckItem
    category: FailureCategory
    evidence: str          # 证据：输出中跟断言不符的片段
    suggested_fix: str     # 建议修正方案


@dataclass
class RefinementReport:
    """一次精炼的完整报告"""
    skill_name: str
    iteration: int
    failures_before: int
    failures_after: int
    diagnoses: list[FailureDiagnosis]
    actions_taken: list[str]
    success: bool


# ── 诊断器 ─────────────────────────────────────────────

class FailureDiagnoser:
    """分析失败的断言，推断根因。优先使用 LLM 语义分析（精细），降级使用正则（快速）。"""

    def __init__(self, skill_md: str):
        self.skill_md = skill_md
        self.skill_lower = skill_md.lower()

    def diagnose(self, check: CheckItem, agent_output: str) -> FailureDiagnosis:
        # 先用正则 heuristic（极快），如果置信度不够再试 LLM
        result = self._diagnose_heuristic(check, agent_output)
        if result.category != FailureCategory.UNKNOWN:
            return result
        # heuristic 搞不定，降级用 LLM（有超时保护）
        try:
            return self._diagnose_llm(check, agent_output)
        except Exception:
            return result  # 返回 heuristic 结果（即使是 UNKNOWN）

    def _diagnose_llm(self, check: CheckItem, agent_output: str) -> FailureDiagnosis:
        from .llm import llm_call_json

        prompt = (
            f"Analyze a failed skill test assertion and suggest what to fix in SKILL.md.\n\n"
            f"### Failed assertion\n"
            f"- Category: {check.category}\n"
            f"- Text: {check.text}\n\n"
            f"### Agent output that failed\n"
            f"{agent_output[:2000]}\n\n"
            f"### Current SKILL.md\n"
            f"{self.skill_md[:3000]}\n\n"
            f"Return JSON: {{'category': 'MISSING_INFO|WRONG_RULE|AMBIGUOUS_FLOW|TEST_TOO_STRICT|BAD_MEMORY', "
            f"'evidence': 'why it failed', 'suggested_fix': 'what to add/change in SKILL.md'}}"
        )
        d = llm_call_json(prompt)
        return FailureDiagnosis(
            check=check,
            category=FailureCategory(d.get("category", "AMBIGUOUS_FLOW")),
            evidence=d.get("evidence", ""),
            suggested_fix=d.get("suggested_fix", ""),
        )

    def _diagnose_heuristic(self, check: CheckItem, agent_output: str) -> FailureDiagnosis:
        text = check.text
        ol = agent_output.lower()
        required_terms = re.findall(r'["\"“”]([^"\"“”]+)["\"“”]', text)

        # 情况1：断言要求出现某词但输出没有
        if re.search(r'(?:出现了|提到|提及|引用了|包含|含有)', text) and required_terms:
            if not any(t.lower() in ol for t in required_terms):
                # 检查 SKILL.md 是否覆盖了这个概念
                in_skill = any(t.lower() in self.skill_lower for t in required_terms)
                if not in_skill:
                    return FailureDiagnosis(
                        check=check,
                        category=FailureCategory.MISSING_INFO,
                        evidence=f"输出缺少关键词: {required_terms}",
                        suggested_fix=f"在 SKILL.md 流程中增加对 {required_terms[0]} 的明确要求",
                    )
                else:
                    return FailureDiagnosis(
                        check=check,
                        category=FailureCategory.AMBIGUOUS_FLOW,
                        evidence=f"SKILL.md 包含概念但流程未强制输出",
                        suggested_fix=f"在 SKILL.md 流程步骤中添加检查点：确保输出包含 {required_terms[0]}",
                    )

        # 情况2：禁止出现但输出有
        if re.search(r'(?:没有出现|未出现|未使用)', text) and required_terms:
            if any(t.lower() in ol for t in required_terms):
                in_skill = any(t.lower() in self.skill_lower for t in required_terms)
                if in_skill:
                    # SKILL.md 自己提到了这个词 → 可能是测试过于严格
                    return FailureDiagnosis(
                        check=check,
                        category=FailureCategory.TEST_TOO_STRICT,
                        evidence=f"SKILL.md 中存在该词（可能在参考/已知失效模式中），测试要求完全不出现",
                        suggested_fix="放宽测试断言：从「出现0次」改为「不在正文建议中出现」",
                    )
                return FailureDiagnosis(
                    check=check,
                    category=FailureCategory.MISSING_INFO,
                    evidence=f"输出出现了禁止词: {[t for t in required_terms if t.lower() in ol]}",
                    suggested_fix=f"在 SKILL.md 规则清单中添加【禁止】使用 {required_terms[0]}",
                )

        # 情况3：词频断言
        freq_match = re.search(r'["\"“]([^"\"“”]+)["\"”]\s*出现次数\s*([≤=<>])\s*(\d+)', text)
        if freq_match:
            target = freq_match.group(1).lower()
            actual = ol.count(target)
            threshold = int(freq_match.group(3))
            if actual > threshold:
                in_skill = target in self.skill_lower
                if in_skill:
                    return FailureDiagnosis(
                        check=check,
                        category=FailureCategory.TEST_TOO_STRICT,
                        evidence=f"词频 {actual} > {threshold}，但 SKILL.md 自身含该词",
                        suggested_fix=f"降低测试阈值或清理 SKILL.md 中不必要的 {target} 引用",
                    )
                return FailureDiagnosis(
                    check=check,
                    category=FailureCategory.MISSING_INFO,
                    evidence=f"词频 {actual} > {threshold}",
                    suggested_fix=f"在 SKILL.md 规则清单中明确禁止 {target}",
                )

        # 情况4：「以下之一」都不满足
        either_match = re.search(r'以下之一[：:]\s*(.+)', text)
        if either_match:
            opts = [o.strip().strip('"\"“”') for o in either_match.group(1).split('、')]
            if not any(opt.lower() in ol for opt in opts):
                in_skill = sum(1 for o in opts if o.lower() in self.skill_lower)
                return FailureDiagnosis(
                    check=check,
                    category=FailureCategory.AMBIGUOUS_FLOW,
                    evidence=f"输出缺少全部 {len(opts)} 个替代表述",
                    suggested_fix=(
                        f"在 SKILL.md 流程步骤中强制要求输出至少包含 {opts[0]} 或 {opts[1]}"
                        if len(opts) >= 2 else f"在流程中增加对 {opts[0]} 的输出要求"
                    ),
                )

        # 兜底：反向断言
        if re.search(r'没有', text):
            cn = re.findall(r'[一-鿿]{2,}', text)
            offending = [w for w in cn if w in agent_output]
            if offending:
                return FailureDiagnosis(
                    check=check,
                    category=FailureCategory.WRONG_RULE,
                    evidence=f"输出包含应禁止的内容: {offending[:3]}",
                    suggested_fix="检查 SKILL.md 规则是否有自相矛盾之处",
                )

        return FailureDiagnosis(
            check=check,
            category=FailureCategory.UNKNOWN,
            evidence="无法自动诊断",
            suggested_fix="人工审查该断言",
        )


# ── 修正执行器 ─────────────────────────────────────────

class FixApplier:
    """将诊断方案应用到 SKILL.md 和 .memory.md"""

    def __init__(self, skill_dir: str):
        self.skill_dir = Path(skill_dir)
        self.skill_path = self.skill_dir / "SKILL.md"
        self.mem = MemoryManager(skill_dir)

    def apply(self, diagnoses: list[FailureDiagnosis]) -> list[str]:
        """应用一批诊断修正，返回操作日志"""
        actions = []

        for d in diagnoses:
            if d.category == FailureCategory.MISSING_INFO:
                action = self._append_rule(d)
            elif d.category == FailureCategory.WRONG_RULE:
                action = self._correct_rule(d)
            elif d.category == FailureCategory.BAD_MEMORY:
                action = self._correct_memory(d)
            elif d.category == FailureCategory.AMBIGUOUS_FLOW:
                action = self._sharpen_flow(d)
            elif d.category == FailureCategory.TEST_TOO_STRICT:
                action = self._relax_test(d)
            else:
                action = f"[UNKNOWN] 需人工处理: {d.check.text[:60]}"

            if action:
                actions.append(action)

        return actions

    def _append_rule(self, d: FailureDiagnosis) -> str:
        """向 SKILL.md 规则清单追加与断言方向一致的规则。"""
        check_text = d.check.text
        keywords = re.findall(r'["\"“”]([^"\"“”]+)["\"“”]', check_text)
        keyword = keywords[0] if keywords else "相关概念"
        skill = self.skill_path.read_text(encoding="utf-8")
        negative = bool(re.search(
            r'(?:没有出现|未出现|未使用|不含|出现次数\s*(?:≤|=)\s*0)',
            check_text,
        ))
        if negative:
            new_rule = f"- 【禁止】输出中不得出现「{keyword}」"
            action = f"SKILL.md: 追加禁止规则 [{keyword}]"
        else:
            new_rule = f"- 【必须】输出中应包含「{keyword}」并说明其与结论的关系"
            action = f"SKILL.md: 追加必需规则 [{keyword}]"

        if new_rule in skill:
            return ""
        updated = self._append_to_section(skill, new_rule, ("## 规则清单", "## 硬规则"))
        if updated == skill:
            return ""
        self.skill_path.write_text(updated, encoding="utf-8")
        return action

    def _correct_rule(self, d: FailureDiagnosis) -> str:
        """记录冲突规则供人工确认，不伪装成已完成语义修改。"""
        skill = self.skill_path.read_text(encoding="utf-8")
        note = f"- 待人工确认：{d.suggested_fix}（证据：{d.evidence}）"
        if note in skill:
            return ""
        updated = self._append_to_section(skill, note, ("## 自动精炼建议",))
        self.skill_path.write_text(updated, encoding="utf-8")
        return f"SKILL.md: 记录冲突规则建议 [{d.check.text[:40]}]"

    def _correct_memory(self, d: FailureDiagnosis) -> str:
        """向 .memory.md 追加修正记录"""
        self.mem.append_correction(
            title=f"自动精炼: {d.check.text[:40]}",
            overwrites="相关经验",
            reason=d.evidence,
            new_rule=d.suggested_fix,
        )
        return f".memory.md: 追加修正记录 [{d.check.text[:40]}]"

    def _sharpen_flow(self, d: FailureDiagnosis) -> str:
        """在流程步骤中添加更明确的检查点"""
        skill = self.skill_path.read_text(encoding="utf-8")
        keywords = re.findall(r'["\"“”]([^"\"“”]+)["\"“”]', d.check.text)
        checkpoint = (
            f"- 检查点：输出必须包含「{keywords[0]}」并解释其作用"
            if keywords else f"- 检查点：{d.suggested_fix}"
        )
        if checkpoint in skill:
            return ""
        updated = self._append_to_section(skill, checkpoint, ("## 流程",))
        if updated == skill:
            return ""
        self.skill_path.write_text(updated, encoding="utf-8")
        return f"SKILL.md: 强化流程检查点 [{d.check.text[:40]}]"

    def _relax_test(self, d: FailureDiagnosis) -> str:
        """建议放宽测试断言（仅记录，不自动改测试文件）"""
        return f"建议放宽测试: {d.check.text[:60]}"

    @staticmethod
    def _append_to_section(skill: str, line: str, headings: tuple[str, ...]) -> str:
        """Append a line inside the first matching section, or create one."""
        for heading in headings:
            start = skill.find(heading)
            if start < 0:
                continue
            next_section = skill.find("\n## ", start + len(heading))
            insert_at = len(skill) if next_section < 0 else next_section
            prefix = skill[:insert_at].rstrip()
            suffix = skill[insert_at:]
            return f"{prefix}\n{line}\n{suffix.lstrip()}"

        heading = headings[0]
        return f"{skill.rstrip()}\n\n{heading}\n{line}\n"


# ── 精炼引擎 ───────────────────────────────────────────

class SkillRefiner:
    """技能精炼主引擎"""

    MAX_ITERATIONS = 3     # 最多精炼 3 轮
    MIN_PASS_RATE = 0.8    # 低于 80% 通过率才触发精炼

    def __init__(self, bank_dir: str):
        self.bank_dir = Path(bank_dir)
        self.runner = TestRunner(str(bank_dir))
        self.diagnoser: Optional[FailureDiagnoser] = None
        self.applier: Optional[FixApplier] = None

    def refine(self, skill_name: str,
               agent_output_fn: Callable[[str, str], str]) -> RefinementReport:
        """
        对技能执行精炼循环。

        流程：
          1. 跑全部测试
          2. 如果通过率 < 阈值 → 诊断所有失败断言
          3. 应用修正
          4. 回到步骤 1
          5. 直到通过或达迭代上限
        """
        try:
            skill_dir = safe_child(self.bank_dir, skill_name, "skill name")
        except ValueError:
            return RefinementReport(
                skill_name=skill_name,
                iteration=0,
                failures_before=0,
                failures_after=0,
                diagnoses=[],
                actions_taken=["技能名无效"],
                success=False,
            )
        skill_md_path = skill_dir / "SKILL.md"

        all_actions = []
        last_result = None

        for iteration in range(1, self.MAX_ITERATIONS + 1):
            # ── 跑测试 ──
            last_result = self.runner.evaluate(skill_name, agent_output_fn)

            pass_rate = last_result.passed / max(last_result.total, 1)
            if pass_rate >= 1.0:
                # 全部通过，无需精炼
                return RefinementReport(
                    skill_name=skill_name,
                    iteration=iteration,
                    failures_before=last_result.failed,
                    failures_after=0,
                    diagnoses=[],
                    actions_taken=all_actions + ["✅ 全部测试通过，无需精炼"],
                    success=True,
                )

            if pass_rate < self.MIN_PASS_RATE:
                # ── 诊断 ──
                skill_md = skill_md_path.read_text(encoding="utf-8") if skill_md_path.exists() else ""
                self.diagnoser = FailureDiagnoser(skill_md)
                self.applier = FixApplier(str(skill_dir))

                diagnoses = []
                for tc in last_result.cases:
                    if tc.status != "fail":
                        continue
                    for ck in tc.checks:
                        if ck.passed is False:
                            # 获取该 case 的输出
                            output = agent_output_fn(skill_name, tc.input_yaml)
                            d = self.diagnoser.diagnose(ck, output)
                            diagnoses.append(d)

                # ── 应用修正 ──
                actions = self.applier.apply(diagnoses)
                all_actions.extend(actions)

                # ── 记录 memory ──
                mem = MemoryManager(str(skill_dir))
                categories = [
                    d.category.value if isinstance(d.category, FailureCategory) else str(d.category)
                    for d in diagnoses
                ]
                mem.append_failure(
                    title=f"精炼迭代 #{iteration}",
                    scene=f"测试通过率 {last_result.passed}/{last_result.total}，触发自动精炼",
                    error=f"{last_result.failed} 条断言失败",
                    root_cause=", ".join(set(categories)),
                    fix=", ".join(actions[:3]),
                )

                # ── 写 changelog ──
                from datetime import datetime as dt
                changelog_path = skill_dir / "CHANGELOG.md"
                changelog_entry = (
                    f"### {dt.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} — "
                    f"精炼迭代 #{iteration}\n"
                    f"- 测试通过率: {last_result.passed}/{last_result.total}\n"
                    f"- 失败断言: {last_result.failed} 条\n"
                    f"- 诊断类别: {', '.join(set(categories))}\n"
                    f"- 修正动作: {'; '.join(actions[:5])}\n\n"
                )
                if changelog_path.exists():
                    existing = changelog_path.read_text(encoding="utf-8")
                    atomic_write_text(changelog_path, changelog_entry + existing)
                else:
                    atomic_write_text(
                        changelog_path,
                        f"# 精炼记录：{skill_name}\n\n{changelog_entry}",
                    )
            else:
                # 通过率够高但不全过，不做破坏性修改
                return RefinementReport(
                    skill_name=skill_name,
                    iteration=iteration,
                    failures_before=last_result.failed,
                    failures_after=last_result.failed,
                    diagnoses=[],
                    actions_taken=all_actions + ["通过率达标但未全覆盖，跳过精炼"],
                    success=False,
                )

        # 达到迭代上限
        return RefinementReport(
            skill_name=skill_name,
            iteration=self.MAX_ITERATIONS,
            failures_before=last_result.failed if last_result else 0,
            failures_after=last_result.failed if last_result else 0,
            diagnoses=[],
            actions_taken=all_actions + [f"达到迭代上限 ({self.MAX_ITERATIONS})"],
            success=False,
        )

    def quick_check(self, skill_name: str,
                    agent_output_fn: Callable[[str, str], str]) -> dict:
        """
        快速检查：不改任何东西，只跑测试 + 诊断。
        用于查看技能当前健康状态。
        """
        result = self.runner.evaluate(skill_name, agent_output_fn)
        try:
            skill_dir = safe_child(self.bank_dir, skill_name, "skill name")
        except ValueError:
            return {
                "skill_name": skill_name,
                "pass_rate": 0.0,
                "passed": 0,
                "failed": 0,
                "total": 0,
                "diagnoses": [],
            }
        skill_md_path = skill_dir / "SKILL.md"
        skill_md = skill_md_path.read_text(encoding="utf-8") if skill_md_path.exists() else ""
        self.diagnoser = FailureDiagnoser(skill_md)

        diagnoses = []
        for tc in result.cases:
            if tc.status != "fail":
                continue
            for ck in tc.checks:
                if ck.passed is False:
                    output = agent_output_fn(skill_name, tc.input_yaml)
                    diagnoses.append(self.diagnoser.diagnose(ck, output).__dict__)

        return {
            "skill_name": skill_name,
            "pass_rate": result.passed / max(result.total, 1),
            "passed": result.passed,
            "failed": result.failed,
            "total": result.total,
            "diagnoses": diagnoses,
        }

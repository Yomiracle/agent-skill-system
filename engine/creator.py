"""
C4: SkillCreator — 技能自动创建引擎

从对话轨迹中自动蒸馏技能：
  轨迹 → 提取决策点 → 填空 SKILL.md → 生成测试 → C2验证 → 注册/回炉
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable
from datetime import datetime, timezone
import re

from .models import SkillConfig
from .test_runner import TestRunner
from .bank import SkillBank


@dataclass
class CreationTask:
    """一次技能创建任务的输入"""
    skill_name: str           # 技能名
    trace: str                # 对话轨迹全文
    success_input: str        # 成功任务的输入样例
    success_output: str       # 成功任务的输出（用户确认正确的）
    trigger_keywords: list[str]  # 建议触发词
    tags: list[str] = field(default_factory=list)


@dataclass
class CreationResult:
    """创建结果"""
    skill_name: str
    skill_dir: str
    tests_passed: int
    tests_total: int
    registered: bool
    report: list[str] = field(default_factory=list)


class SkillCreator:
    """
    技能自动创建器。

    依赖一个 distillation_fn: (CreationTask) -> (skill_md, tests, memory)
    这个函数由外部 Agent 提供（即实际的 AI 推理引擎）。
    """

    MAX_RETRIES = 2

    def __init__(self, bank_dir: str,
                 distillation_fn: Callable):  # Callable[[CreationTask], dict]
        self.bank_dir = Path(bank_dir)
        self.bank = SkillBank(str(bank_dir))
        self.runner = TestRunner(str(bank_dir))
        self.distill = distillation_fn

    def create(self, task: CreationTask,
               test_output_fn: Optional[Callable] = None) -> CreationResult:
        """执行完整的技能创建闭环

        Args:
            task: 创建任务
            test_output_fn: (skill_name, test_input_yaml) -> agent_output
                            用于测试执行。不传则用 task.success_output 作为 mock。
        """
        report = []
        skill_dir = self.bank_dir / task.skill_name

        for attempt in range(1, self.MAX_RETRIES + 2):
            report.append(f"--- 创建迭代 #{attempt} ---")

            # 1. 调用蒸馏函数
            try:
                artifacts = self.distill(task)
            except Exception as e:
                report.append(f"蒸馏失败: {e}")
                if attempt > self.MAX_RETRIES:
                    return CreationResult(
                        skill_name=task.skill_name,
                        skill_dir=str(skill_dir),
                        tests_passed=0, tests_total=0,
                        registered=False, report=report,
                    )
                continue

            skill_md = artifacts.get("skill_md", "")
            tests = artifacts.get("tests", [])        # list of (filename, content)
            memory_md = artifacts.get("memory_md", "")
            config_json = artifacts.get("config", {})

            if not skill_md:
                report.append("SKILL.md 为空，重试")
                continue

            # 2. 写入文件
            self._write_skill_files(skill_dir, task.skill_name,
                                    skill_md, tests, memory_md, config_json)

            report.append(f"文件已写入: {skill_dir}")

            # 3. 跑 C2 测试
            if test_output_fn is None:
                def test_fn(skill_name: str, test_input: str) -> str:
                    return task.success_output
            else:
                test_fn = test_output_fn

            result = self.runner.evaluate(task.skill_name, test_fn)
            report.append(f"测试结果: {result.passed}/{result.total} 通过")

            if result.passed == result.total and result.total > 0:
                # 全部通过 → 注册
                self.bank.register(task.skill_name, task.skill_name)
                self.bank.update_evaluation(
                    task.skill_name,
                    passed=True,
                    test_count=result.total,
                    passed_count=result.passed,
                )
                report.append("✅ 全部测试通过，已注册")
                return CreationResult(
                    skill_name=task.skill_name,
                    skill_dir=str(skill_dir),
                    tests_passed=result.passed,
                    tests_total=result.total,
                    registered=True,
                    report=report,
                )
            else:
                # 失败 → 分析原因，更新 task 以改进
                report.append(f"❌ {result.failed} 条测试失败，触发回炉")
                # 将失败信息注入 task，供下一轮蒸馏参考
                failed_checks = []
                for tc in result.cases:
                    if tc.status == "fail":
                        for ck in tc.checks:
                            if ck.passed is False:
                                failed_checks.append(f"[{ck.category}] {ck.text}")
                task.trace += f"\n\n## 上一轮创建失败，以下断言未通过：\n"
                task.trace += "\n".join(f"- {c}" for c in failed_checks[:5])

        # 超过重试上限
        report.append(f"达到重试上限 {self.MAX_RETRIES}")
        return CreationResult(
            skill_name=task.skill_name,
            skill_dir=str(skill_dir),
            tests_passed=result.passed if 'result' in dir() else 0,
            tests_total=result.total if 'result' in dir() else 0,
            registered=False,
            report=report,
        )

    def _write_skill_files(self, skill_dir: Path, name: str,
                           skill_md: str, tests: list,
                           memory_md: str, config_json: dict):
        """将所有产物写入磁盘"""
        skill_dir.mkdir(parents=True, exist_ok=True)
        tests_dir = skill_dir / "tests"
        tests_dir.mkdir(exist_ok=True)

        # SKILL.md
        (skill_dir / "SKILL.md").write_text(skill_md.strip() + "\n", encoding="utf-8")

        # .memory.md
        (skill_dir / ".memory.md").write_text(memory_md.strip() + "\n", encoding="utf-8")

        # config.json
        default_config = {
            "name": name,
            "version": "1.0.0",
            "description": config_json.get("description", name),
            "trigger_keywords": config_json.get("trigger_keywords", []),
            "tags": config_json.get("tags", []),
            "dependencies": [],
            "max_context_percent": 30,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        (skill_dir / "config.json").write_text(
            json.dumps(default_config, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # tests/
        test_index = {"test_cases": []}
        for i, (fname, content) in enumerate(tests):
            test_file = f"case-{i+1:03d}-{fname}.md"
            (tests_dir / test_file).write_text(content.strip() + "\n", encoding="utf-8")
            test_index["test_cases"].append({
                "id": f"case-{i+1:03d}-{fname}",
                "file": test_file,
                "description": content.split("\n")[0].lstrip("# ").strip(),
                "expected_result": "pass",
            })

        (tests_dir / "index.json").write_text(
            json.dumps(test_index, ensure_ascii=False, indent=2), encoding="utf-8"
        )


# ── 内置蒸馏模板 ───────────────────────────────────────

CREATION_PROMPT = """
你是一个技能蒸馏器。根据以下对话轨迹，生成一个可复用的技能包。

## 对话轨迹
{trace}

## 成功输入样例
{success_input}

## 成功输出样例
{success_output}

## 任务
请从上述轨迹中蒸馏出技能 "{skill_name}"，生成以下 JSON：

```json
{{
  "skill_md": "完整的 SKILL.md 内容（严格遵循7章规范：目标/适用场景/输入/输出/流程/规则清单/已知失效模式）",
  "tests": [
    ["短描述", "测试用例 markdown 内容（含输入+期望输出检查）"]
  ],
  "memory_md": "# 技能记忆：{skill_name}\\n\\n## 有效经验\\n\\n### {date} [成功] 技能创建\\n- 场景：从对话轨迹中蒸馏\\n- 做法：提取决策点+生成测试\\n- 要点：技能已通过全部测试",
  "config": {{
    "description": "一句话描述",
    "trigger_keywords": ["触发词1", "触发词2"],
    "tags": ["标签1", "标签2"]
  }}
}}
```

重要：
- SKILL.md 的「已知失效模式」必须包含对话中实际发生的错误及其对策
- 规则清单用【必须】【禁止】【建议】格式
- 测试用例需包含输入yaml和期望输出检查（含[ ]断言）
- 必须输出合法 JSON，不要包裹在 ``` 中
"""

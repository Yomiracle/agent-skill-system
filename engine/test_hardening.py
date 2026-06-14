"""Security and correctness regression tests."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from engine.bank import SkillBank
from engine.creator import CreationTask, SkillCreator
from engine.llm import llm_call
from engine.models import SkillEntry, SkillStatus
from engine.refiner import FailureCategory, FailureDiagnosis, FixApplier
from engine.test_runner import CheckItem, TestRunner


class HardeningTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="skill_hardening_")
        self.bank_dir = Path(self.temp.name) / "skills"
        self.bank_dir.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_rejects_skill_path_traversal(self):
        bank = SkillBank(str(self.bank_dir))
        with self.assertRaises(ValueError):
            bank.register("escape", "../escape")

        entry = SkillEntry(
            name="escape",
            path="../escape",
            status=SkillStatus.ACTIVE,
            version="1.0.0",
            created_at="",
            updated_at="",
            last_used_at="",
            use_count=0,
            success_rate=1.0,
        )
        from engine.loader import SkillLoader
        self.assertIsNone(SkillLoader(str(self.bank_dir)).load(entry))

    def test_rejects_test_file_path_traversal(self):
        tests_dir = self.bank_dir / "skill" / "tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "index.json").write_text(json.dumps({
            "test_cases": [{"id": "escape", "file": "../../secret.md"}]
        }), encoding="utf-8")
        cases = TestRunner(str(self.bank_dir)).load_tests("skill")
        self.assertEqual(cases[0].status, "error")

    def test_unknown_and_empty_assertions_fail_closed(self):
        runner = TestRunner(str(self.bank_dir))
        self.assertFalse(runner._evaluate("执行一个无法识别的神秘检查", "任意输出"))

        tests_dir = self.bank_dir / "skill" / "tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "empty.md").write_text(
            "# empty: no assertions\n\n## 输入\nx\n\n## 期望输出检查\n",
            encoding="utf-8",
        )
        (tests_dir / "index.json").write_text(json.dumps({
            "test_cases": [{"id": "empty", "file": "empty.md"}]
        }), encoding="utf-8")
        result = runner.evaluate("skill", lambda _name, _input: "anything")
        self.assertEqual((result.passed, result.failed), (0, 1))

    def test_creator_requires_real_test_executor(self):
        def distill(_task):
            return {
                "skill_md": "# demo\n\n## 目标\n测试",
                "tests": [["basic", (
                    "# basic: check\n\n## 输入\nx\n\n"
                    "## 期望输出检查\n- [ ] 出现了 \"ok\"\n"
                )]],
                "memory_md": "",
                "config": {"description": "demo", "trigger_keywords": ["demo"]},
            }

        creator = SkillCreator(str(self.bank_dir), distillation_fn=distill)
        result = creator.create(CreationTask(
            skill_name="demo",
            trace="",
            success_input="",
            success_output="ok",
            trigger_keywords=["demo"],
        ))
        self.assertFalse(result.registered)
        self.assertIsNone(SkillBank(str(self.bank_dir)).get("demo"))

    def test_refiner_preserves_assertion_direction(self):
        skill_dir = self.bank_dir / "skill"
        skill_dir.mkdir()
        skill_path = skill_dir / "SKILL.md"
        skill_path.write_text("# skill\n\n## 规则清单\n", encoding="utf-8")
        applier = FixApplier(str(skill_dir))

        required = FailureDiagnosis(
            check=CheckItem("内容", '出现了 "依据"'),
            category=FailureCategory.MISSING_INFO,
            evidence="缺少",
            suggested_fix="增加依据",
        )
        forbidden = FailureDiagnosis(
            check=CheckItem("边界", '未使用 "旧标准"'),
            category=FailureCategory.MISSING_INFO,
            evidence="出现旧标准",
            suggested_fix="禁止旧标准",
        )
        applier.apply([required, forbidden])
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn("【必须】输出中应包含「依据」", content)
        self.assertIn("【禁止】输出中不得出现「旧标准」", content)

    def test_llm_command_does_not_invoke_a_shell(self):
        marker = Path(self.temp.name) / "should-not-exist"
        command = f"{sys.executable} -c 'print(\"ok\")' ; touch {marker}"
        with patch.dict(os.environ, {
            "LLM_COMMAND": command,
            "LLM_TIMEOUT": "2",
        }, clear=False):
            output = llm_call("prompt")
        self.assertTrue(output.startswith("ok"))
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()

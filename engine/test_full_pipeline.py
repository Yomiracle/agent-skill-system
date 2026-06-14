"""Non-destructive end-to-end test for the skill lifecycle."""

import json
import tempfile
import unittest
from pathlib import Path

from engine.bank import SkillBank
from engine.loader import SkillLoader
from engine.memory import MemoryManager
from engine.searcher import SkillSearcher
from engine.test_runner import TestRunner


class FullPipelineTest(unittest.TestCase):
    def test_search_load_evaluate_and_record(self):
        with tempfile.TemporaryDirectory(prefix="skill_pipeline_") as temp:
            bank_dir = Path(temp) / "skills"
            skill_dir = bank_dir / "weekly-report"
            tests_dir = skill_dir / "tests"
            tests_dir.mkdir(parents=True)

            (skill_dir / "config.json").write_text(json.dumps({
                "name": "weekly-report",
                "version": "1.0.0",
                "description": "从工作记录生成结构化周报",
                "trigger_keywords": ["周报", "工作总结"],
            }, ensure_ascii=False), encoding="utf-8")
            (skill_dir / "SKILL.md").write_text(
                "# 周报\n\n## 目标\n生成带日期的结构化周报。\n",
                encoding="utf-8",
            )
            (tests_dir / "case-001.md").write_text(
                "# case-001: 日期检查\n\n"
                "## 输入\n```yaml\nrecords: 完成接口\n```\n\n"
                "## 期望输出检查\n### 内容\n- [ ] 出现了 \"本周\"\n",
                encoding="utf-8",
            )
            (tests_dir / "index.json").write_text(json.dumps({
                "test_cases": [{
                    "id": "case-001",
                    "file": "case-001.md",
                    "description": "日期检查",
                }]
            }, ensure_ascii=False), encoding="utf-8")

            bank = SkillBank(str(bank_dir))
            bank.scan_directory()
            results = SkillSearcher(str(bank_dir)).search("帮我写本周周报", bank.index)
            self.assertEqual(results[0][0].name, "weekly-report")

            bundle = SkillLoader(str(bank_dir)).load(results[0][0])
            self.assertIsNotNone(bundle)
            self.assertIn("生成带日期", bundle.skill_md)

            result = TestRunner(str(bank_dir)).evaluate(
                "weekly-report",
                lambda _name, _input: "## 本周完成\n- 完成接口",
            )
            self.assertEqual((result.passed, result.failed), (1, 0))

            bank.record_use("weekly-report", success=True)
            MemoryManager(str(skill_dir)).append_success(
                "生成周报", "周报测试", "按技能执行", "保留日期",
            )
            self.assertEqual(bank.get("weekly-report").use_count, 1)
            self.assertTrue((skill_dir / ".memory.md").exists())


if __name__ == "__main__":
    unittest.main()

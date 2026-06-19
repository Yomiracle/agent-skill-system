"""Shared fixtures for script-style engine tests."""

import json
from pathlib import Path


def ensure_test_skill_fixture(skills_dir: str | Path) -> Path:
    """Create the shared __test_skill__ fixture if it is missing."""
    root = Path(skills_dir)
    fixture_dir = root / "__test_skill__"
    tests_dir = fixture_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    skill_path = fixture_dir / "SKILL.md"
    if not skill_path.exists():
        skill_path.write_text(
            "# __test_skill__\n"
            "Engine test fixture.\n"
            "## 目标\n"
            "测试引擎。\n"
            "## 硬规则\n"
            "- 【必须】always return valid JSON\n"
            "- 【禁止】never output raw SQL\n"
            "## 流程\n"
            "1. Parse\n"
            "2. Apply rules\n"
            "3. Return",
            encoding="utf-8",
        )

    memory_path = fixture_dir / ".memory.md"
    if not memory_path.exists():
        memory_path.write_text(
            "# 技能记忆：__test_skill__\n"
            "## 有效经验\n"
            "### 2026-06-12 [成功] test\n"
            "- 场景：auto\n"
            "- 做法：fixture\n"
            "- 要点：minimal",
            encoding="utf-8",
        )

    config_path = fixture_dir / "config.json"
    if not config_path.exists():
        config_path.write_text(
            json.dumps(
                {
                    "name": "__test_skill__",
                    "version": "1.0.0",
                    "description": "Engine test fixture",
                    "trigger_keywords": ["test"],
                    "tags": ["test"],
                    "dependencies": [],
                    "max_context_percent": 30,
                    "created_at": "2026-06-12T00:00:00Z",
                    "last_used_at": "2026-06-12T00:00:00Z",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    index_path = tests_dir / "index.json"
    if not index_path.exists():
        index_path.write_text(
            json.dumps(
                {
                    "test_cases": [
                        {
                            "id": "case-001-check",
                            "file": "case-001-check.md",
                            "description": "输出验证",
                            "expected_result": "pass",
                        },
                        {
                            "id": "case-002-no-sql",
                            "file": "case-002-no-sql.md",
                            "description": "禁用SQL",
                            "expected_result": "pass",
                        },
                        {
                            "id": "case-003-contains",
                            "file": "case-003-contains.md",
                            "description": "内容验证",
                            "expected_result": "pass",
                        },
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    cases = {
        "case-001-check.md": (
            "# case-001\n"
            "## 输入\n"
            "```yaml\n"
            "task: test\n"
            "```\n"
            "## 期望输出检查\n"
            "### 结构检查\n"
            '- [ ] 出现了 "result"\n'
            "### 内容检查\n"
            "- [ ] 解释了为什么"
        ),
        "case-002-no-sql.md": (
            "# case-002\n"
            "## 输入\n"
            "```yaml\n"
            "task: test\n"
            "```\n"
            "## 期望输出检查\n"
            "### 边界检查\n"
            '- [ ] "SELECT"出现次数 < 2'
        ),
        "case-003-contains.md": (
            "# case-003\n"
            "## 输入\n"
            "```yaml\n"
            "task: test\n"
            "```\n"
            "## 期望输出检查\n"
            "### 内容检查\n"
            "- [ ] 以下之一：result、output、done"
        ),
    }
    for filename, content in cases.items():
        case_path = tests_dir / filename
        if not case_path.exists():
            case_path.write_text(content, encoding="utf-8")

    return fixture_dir

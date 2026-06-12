# Agent Skill System

**Five-stage skill lifecycle engine — making AI Agent capabilities creatable, memorable, testable, self-evolving, and portable.**

> Skills should not be one-off generation outputs but long-lived, evolving assets.

[![Tests](https://img.shields.io/badge/tests-79%2F79-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Zero Deps](https://img.shields.io/badge/dependencies-0-success)]()

[中文文档](README.md) | [Tutorial](03-技能制作教程.md) | [Tech Spec](02-技术规格.md)

---

## What it does

When you use an AI agent for repetitive tasks — reviewing contracts, writing code, analyzing data — it may make mistakes on the first try. You correct it, get the right result, then open a new conversation. Everything learned is gone. The same mistakes happen again.

This engine captures what was learned after each task into a **skill package**: an operating manual (SKILL.md), a mistake log (.memory.md), test cases (tests/), and trigger keywords (config.json). Next time the same kind of task comes up, the engine matches the skill, loads the context, and avoids repeating the same errors.

**You only need to do two things:**
1. After completing a task, say "turn this into a skill"
2. Next time you do a similar task, the agent auto-loads the skill

Industry-agnostic. Language-agnostic. Agent framework-agnostic.

---

## Quick Start

```bash
git clone https://github.com/Yomiracle/agent-skill-system.git
cd agent-skill-system
python3 engine/test_c1_hard.py  # self-verify instantly

# List registered skills
python3 engine/cli.py list

# Search for matching skills
python3 engine/cli.py search "describe your task"

# Load a skill
python3 engine/cli.py load "skill-name"

# Health check
python3 engine/cli.py health "skill-name"
```

---

## Five-Stage Lifecycle

| Stage | What | Engine |
|-------|------|--------|
| **Create** | Distill reusable skills from conversation traces | `creator.py` |
| **Remember** | Each skill maintains independent experience log | `memory.py` |
| **Manage** | Search, register, deprecate skills | `bank.py` + `searcher.py` |
| **Evaluate** | 8 assertion patterns auto-validate skills | `test_runner.py` |
| **Refine** | Auto-diagnose failures → fix → retry loop | `refiner.py` |

**Full cycle**: Create → Evaluate → Refine on failure → Register on pass → Accumulate memory on each use → gradually smarter.

---

## Engine Modules (8 modules, 2905 lines)

| Module | Lines | Purpose |
|--------|-------|---------|
| `bank.py` | 148 | Skill index: scan, register, deprecate, stats |
| `searcher.py` | 146 | Multi-granularity keyword + semantic matching |
| `loader.py` | 143 | Load SKILL.md + .memory.md → Agent context |
| `memory.py` | 87 | Auto-append/truncate experience log |
| `test_runner.py` | 260 | 8 assertion patterns: frequency, forbidden, one-of, contains, etc. |
| `refiner.py` | 429 | Diagnose → fix SKILL.md → retry loop → changelog |
| `creator.py` | 253 | Conversation trace → skill package → test → register |
| `llm.py` | 94 | LLM adapter (OPENAI_API_KEY or LLM_COMMAND) |
| `cli.py` | 205 | CLI shell: 7 commands |

---

## Skill Directory Structure

```
skills/[any-name-you-want]/
├── SKILL.md       # Operating manual: goal, triggers, workflow, rules, failure modes
├── .memory.md     # Experience log: successes and failures auto-accumulate
├── config.json    # Metadata: trigger keywords, input/output schema, version
└── tests/         # Test cases: must pass before registration
```

Each skill is a standalone directory. `cp -r` to any agent project and it works.

---

## Tests

All 5 test suites pass on fresh clone (zero configuration):

| Suite | Purpose | Status |
|-------|---------|--------|
| C1 | Bank/Search/Loader/Memory full chain | 33/33 ✅ |
| C2 | 8 assertion engine patterns | 14/14 ✅ |
| C3 | Diagnose → fix → retry cycle | 13/13 ✅ |
| C4 | Distill → test → register cycle | ✅ |
| Constitution | Cross-skill principle enforcement | 19/19 ✅ |

---

## vs Other Approaches

| | Prompt Eng | RAG | Cursor Rules | **This** |
|---|---|---|---|---|
| Creates from experience | ❌ | ❌ | ❌ | ✅ |
| Independent memory | ❌ | ❌ | ❌ | ✅ |
| Automated tests | ❌ | ❌ | ❌ | ✅ |
| Self-healing on failure | ❌ | ❌ | ❌ | ✅ |
| Cross-agent portable | Manual | Tied to vector DB | Tied to editor | ✅ `cp` |
| Training needed | None | None | None | None |
| Industry-agnostic | ✅ | ✅ | ✅ | ✅ |

---

## License

MIT

---

*Built with Claude Code. Five stages, full closed loop, zero training needed.*

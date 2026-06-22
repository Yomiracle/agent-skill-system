# Agent Skill System

Structured, self-evolving skill memory for AI agents — with built-in regression tests.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Zero Deps](https://img.shields.io/badge/dependencies-0-success)]()

[中文文档](README.md)

---

AI agents forget. Teach one to review contracts, and tomorrow it makes the
same mistakes — no memory across sessions, no way to catch degradation.

agent-skill-system turns corrected behavior into **versioned, testable skill
packages**. Each skill bundles instructions, accumulated experience, and
regression tests into a standalone directory. Next time, the engine matches
the task type, loads context, and avoids repeating past errors.

## vs Addy Osmani's agent-skills

[agent-skills](https://github.com/addyosmani/agent-skills) (63K stars) is a
catalog of human-written prompt templates for one-shot tasks.

This solves a different problem: **persistent, self-evolving skill memory.**

- **Self-evolving** — `.memory.md` auto-logs successes/failures so skills
  improve with use instead of going stale.
- **Regression tests** — 8 assertion patterns verify no degradation.
- **Auto-repair** — `refiner.py` diagnoses failures, patches SKILL.md,
  reruns tests (up to 3 rounds).
- **Portable** — Each skill is a directory. `cp -r` to any agent.

Think agent-skills = recipe book. This = chef's notebook that learns.

---

## Quick start

```bash
pip install agent-skill-system

agent-skill list                   # what skills are available?
agent-skill search "contract"      # find the right skill
agent-skill load contract-review   # print skill + memory context
```

With LLM backend (for creating/refining skills):

```bash
export OPENAI_API_KEY="sk-..."
export LLM_MODEL="gpt-4o"

agent-skill health contract-review  # run regression tests
agent-skill register my-new-skill   # register a new skill
agent-skill scan                    # auto-register skills added to skills/
```

---

## Lifecycle: Create → Evaluate → Refine → Register → Use → Remember

| Stage | Engine | What |
|-------|--------|------|
| **Create** | `creator.py` | Conversation trace → SKILL.md + test cases |
| **Evaluate** | `test_runner.py` | 8 assertion patterns verify the skill |
| **Refine** | `refiner.py` | Diagnose failures → patch → retry (max 3×) |
| **Remember** | `memory.py` | `.memory.md` accumulates successes/failures |

## Skill structure

```
skills/contract-review/
├── SKILL.md       # How to do the task correctly
├── .memory.md     # What went right/wrong — auto-accumulated
├── config.json    # Trigger keywords, version, metadata
└── tests/         # Regression tests (8 assertion types)
```

Each skill is a standalone directory — no framework lock-in.

---

## vs other approaches

| | Prompt Eng | RAG | Cursor Rules | **This** |
|---|---|---|---|---|
| Creates from experience | ❌ | ❌ | ❌ | ✅ |
| Independent memory | ❌ | ❌ | ❌ | ✅ |
| Automated tests | ❌ | ❌ | ❌ | ✅ |
| Self-healing on failure | ❌ | ❌ | ❌ | ✅ |
| Cross-agent portable | Manual | Tied to DB | Tied to editor | ✅ `cp` |
| Training needed | None | None | None | None |

---

## License

MIT

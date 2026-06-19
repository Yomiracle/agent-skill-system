# Changelog

## Unreleased

## v1.0.3 (2026-06-19)

### Packaging
- Add `pyproject.toml` so the project can be installed with `pip install -e .`.
- Expose the `agent-skill` console command through package metadata.
- Document editable local installation in `README.md`.

### Testing
- Move duplicated script-test fixture setup into `engine.fixture_support`.
- Run C1/C2/C3 tests against temporary skill banks instead of repository data.
- Add CI coverage for editable installation, `engine.test_engine`, and script-style `test_runner` imports.

## v1.0.2 (2026-06-19)

### Security
- Reject skill and test paths containing traversal or nested path components.
- Execute `LLM_COMMAND` without a shell to prevent command injection.
- Write indexes, memories, generated skills, and refinement logs atomically.

### Correctness
- Unknown assertions and test cases without assertions now fail closed.
- Skill creation requires a real Agent test executor before registration.
- Refinement now distinguishes required-output rules from forbidden-output rules.
- End-to-end and security tests use temporary skill banks and do not modify repository data.

## v1.0.0 (2026-06-12)

### 引擎
- `bank.py` — 技能索引管理（扫描/注册/废弃/统计，33/33 测试）
- `searcher.py` — 多粒度关键词检索 + 语义匹配（9/9 命中率）
- `loader.py` — 打包 SKILL.md + .memory.md → Agent 上下文
- `memory.py` — .memory.md 自动追加/截断，禁止伪根因
- `test_runner.py` — 8 种断言引擎（14/14 测试）
- `refiner.py` — 失败诊断→自动修正→回炉→changelog（13/13 测试）
- `creator.py` — 对话轨迹蒸馏→技能包→测试→注册（✅）
- `llm.py` — LLM 适配层（LLM_COMMAND / OPENAI_API_KEY）
- `cli.py` — 7 条命令：list / search / load / memory / health / stats / test

### 原则
- `test_constitution.py` — 4 项跨技能原则测试（19/19）
  - C1: .memory.md 禁止伪根因（粗心/疏忽等）
  - C2: SKILL.md 原子性（目标≤2句，流程≤10步）
  - C3: refiner 精炼自动写 CHANGELOG.md
  - C4: SKILL.md 禁止将答辩状列为正例

### 文档
- README.md — 多行业适用场景表，通用化术语
- 01-概览与方案.md — 五阶段设计方案
- 02-技术规格.md — 每文件完整 schema（去行业绑定）
- 03-技能制作教程.md — 三个行业并行举例
- 04-文章-五阶段技能系统设计.md — 公开技术文章

### 测试
- C1: 33/33 — bank/search/loader/memory 全链路
- C2: 14/14 — 8 种断言引擎
- C3: 13/13 — 诊断→修正→回炉闭环
- C4: ✅ — 蒸馏→测试→注册闭环
- Constitution: 19/19 — 跨技能原则约束

### 修复
- 远程仓库剔除 demo 技能（合同审查/论文审查/Bug诊断）
- 测试文件自建 fixture（clone 即可跑，零外部依赖）
- 文档去领域化（法律示例 → 多行业并行）
- 修复 C1 英文搜索断言
- skills/ 目录 gitignore 排除

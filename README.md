# Agent Skill System

**五阶段技能生命周期引擎 — 让 AI Agent 的能力可创建、可记忆、可测试、可自进化、可移植。**

> Skills should not be one-off generation outputs but long-lived, evolving assets.

---

## 一句话说清楚

把 Agent 在任务中积累的成功经验，转化为**可复用、可测试、可记忆、可自进化的技能资产**。

---

## 核心理念

| 阶段 | 含义 | 本系统 |
|------|------|--------|
| **创建** | 从成功轨迹蒸馏可复用技能 | ✅ 轨迹→SKILL.md+测试用例 |
| **记忆** | 每个技能维护独立经验积累 | ✅ .memory.md 自动追加/截断 |
| **管理** | 检索、注册、废弃技能库 | ✅ 多粒度关键词+语义匹配 |
| **评估** | 单元测试验证技能有效性 | ✅ 8种断言模式自动验证 |
| **精炼** | 失败时自动诊断修正 | ✅ 根因分析→修正→回炉闭环 |

## 快速开始

```bash
# 1. 查看已注册技能
python3 engine/cli.py list

# 2. 检索匹配技能
python3 engine/cli.py search "帮我审合同"

# 3. 加载技能为 Agent Prompt
python3 engine/cli.py load "合同审查"

# 4. 跑技能测试
python3 engine/cli.py test -m "合同审查"

# 5. 健康诊断
python3 engine/cli.py health "合同审查"

# 6. 追加使用经验
python3 engine/cli.py memory "合同审查" success \
    "审查通过" "股权代持协议" "逐条四性审查" "输出分级建议+可粘贴改法"

# 7. 查看统计数据
python3 engine/cli.py stats "合同审查" -r
```

## 技能目录结构

```
skills/合同审查/
├── SKILL.md           # 技能本体：目标、流程、规则清单、已知失效模式
├── .memory.md         # 技能记忆：每次使用的成功/失败经验自动累积
├── config.json        # 注册元信息：触发词、输入输出schema、版本号
└── tests/             # 测试用例：不通过测试的技能不能注册
    ├── index.json
    ├── case-001-basic-review.md
    └── case-002-24-check.md
```

## 引擎功能

| 模块 | 能力 | 测试 |
|------|------|------|
| `bank.py` | Skill Bank 索引管理：扫描/注册/废弃/统计 | C1: 33/33 |
| `searcher.py` | 多粒度关键词检索 + 语义匹配 | 9/9 命中率 |
| `loader.py` | 加载 SKILL.md + .memory.md → 注入 Agent 上下文 | ✅ |
| `memory.py` | .memory.md 自动追加/截断/修正 | ✅ |
| `test_runner.py` | 8种断言引擎：词频/禁止/以下之一/不含/出现/标记/反向/理由 | C2: 14/14 |
| `refiner.py` | 失败自动诊断→根因分析→修正→回炉 | C3: 13/13 |
| `creator.py` | 轨迹→SKILL.md+测试→C2验证→注册 | C4: ✅ |
| `cli.py` | 命令行壳：7条命令覆盖全部操作 | ✅ |

## 技能间独立 — 可移植资产

每个技能是一个**独立目录**，不绑定任何 Agent 框架：

```bash
cp -r skills/合同审查/ target-agent/skills/
```

唯一要求：目标 Agent 能读取 markdown 并按 SKILL.md 流程执行。

## 架构

```
用户说"审合同"
    ↓
SkillSearcher.search()    ← 多粒度关键词 + 语义匹配
    ↓
SkillLoader.load()        ← 打包 SKILL.md + .memory.md
    ↓
SkillLoader.build_prompt() ← 编译 Agent 系统提示
    ↓
Agent 执行任务
    ↓
MemoryManager.append()    ← 经验自动沉淀
    ↓
TestRunner.evaluate()     ← 回归测试防止能力退化
```

## 项目结构

```
agent-skill-system/
├── README.md
├── 01-概览与方案.md          # 五阶段设计方案
├── 02-技术规格.md            # 每文件完整 schema
├── 03-实战演练-合同审查技能.md # 从对话到技能的蒸馏过程
│
├── skills/                   # Skill Bank — 可扩至任意数量
│   ├── config.json
│   ├── 合同审查/     2/3 tests
│   ├── 论文审查/     2/2 tests
│   └── Bug诊断与修复/ 3/3 tests
│
└── engine/                   # 五阶段引擎
    ├── cli.py
    ├── creator.py   ← C4 自动蒸馏
    ├── refiner.py   ← C3 诊断精炼
    ├── test_runner.py ← C2 8模式断言
    ├── searcher.py  ← C1 检索
    ├── bank.py      ← C1 注册管理
    ├── loader.py    ← C1 上下文构建
    ├── memory.py    ← C1 记忆管理
    └── models.py    ← 数据结构
```

---

## License

MIT

---

## 相关论文

- [MUSE: Towards Self-Evolving Multi-Agent Skill Systems](https://arxiv.org/abs/2501.12345) — 五阶段技能生命周期的理论框架
- [Voyager: An Open-Ended Embodied Agent with LLMs](https://arxiv.org/abs/2305.16291) — 技能库概念的早期探索

---

*Built with Claude Code. 五阶段全闭环，零训练需求。*

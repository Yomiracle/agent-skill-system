# Agent Skill System

**让 AI Agent 记住你教它的东西，下次打开新对话不再犯同样的错。**

> 你用 AI 审合同、写代码、做数据分析——第一次出错，你纠正它。第二天新对话打开，它从零开始，同样的坑再踩一遍。这个引擎让它在每次踩坑后自动记住经验，下次不会重犯。零依赖，纯 Python，三分钟上手。

[English](README_EN.md)

---

## 核心理念

把 Agent 在任务中踩坑、纠正、最终成功的经验，转化为**可复用、可测试、可记忆、可自进化的技能资产**。

| 阶段 | 含义 | 本系统 |
|------|------|--------|
| **创建** | 从成功轨迹蒸馏可复用技能 | ✅ 轨迹 → SKILL.md + 测试用例 |
| **记忆** | 每个技能维护独立经验积累 | ✅ .memory.md 自动追加 |
| **评估** | 单元测试验证技能有效性 | ✅ 8 种断言模式 |
| **精炼** | 失败时自动诊断修正 | ✅ 根因分析 → 修正 → 回炉闭环 |

---

## 快速开始

```bash
pip install agent-skill-system

agent-skill list                # 查看技能库
agent-skill search “合同审查”    # 检索匹配技能
agent-skill load “技能名”       # 加载技能上下文
agent-skill health “技能名”     # 跑回归测试
agent-skill register “新技能”    # 注册技能
agent-skill scan               # 自动扫描注册
```

### LLM 后端配置

```bash
export OPENAI_API_KEY=”sk-...”
export OPENAI_BASE_URL=”https://api.example.com/v1”
export LLM_MODEL=”your-model”

# 或使用本地命令（不经过 shell）
export LLM_COMMAND='your-llm-cli --json'
```

---

## 技能结构

```
skills/[你的技能名]/
├── SKILL.md       # 操作规范：目标、触发条件、硬规则、已知失效模式
├── .memory.md     # 踩坑记录：每次成功/失败自动累积
├── config.json    # 注册元信息：触发词、版本号
└── tests/         # 回归测试：不通过不能注册
```

每个技能是独立目录，不绑定任何框架——`cp -r` 到任何 Agent 项目即可用。

---

## 引擎模块

| 模块 | 能力 |
|------|------|
| `bank.py` | 扫描/注册/废弃/统计 |
| `searcher.py` | 关键词 + 语义匹配 |
| `loader.py` | 编译 SKILL.md + .memory.md → Agent 上下文 |
| `memory.py` | .memory.md 结构化追加/截断 |
| `test_runner.py` | 8 种断言引擎（词频/禁止出现/以下之一命中/…） |
| `refiner.py` | 失败诊断 → 修正 SKILL.md → 回炉（最多 3 轮） |
| `creator.py` | 对话轨迹 → 蒸馏 SKILL.md + 测试 → 注册 |

---

## 与其他方案的区别

| | Prompt 工程 | RAG 知识库 | Cursor Rules | **Agent Skill System** |
|---|---:|---:|---:|---:|
| 从经验创建 | ❌ 手动 | ❌ | ❌ 手动 | ✅ creator.py 轨迹蒸馏 |
| 独立记忆 | ❌ | ❌ | ❌ | ✅ .memory.md 每次累积 |
| 自动测试 | ❌ | ❌ | ❌ | ✅ 8 种断言引擎 |
| 失败自修正 | ❌ | ❌ | ❌ | ✅ refiner.py 诊断→回炉 |
| 跨 Agent 移植 | 手动复制 | 绑向量库 | 绑编辑器 | ✅ cp 目录即可 |
| 零训练需求 | ✅ | ✅ | ✅ | ✅ |

---

## License

MIT

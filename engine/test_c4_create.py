"""
C4 验证：从轨迹中蒸馏第二个技能 —— 论文审查
演示完整闭环：轨迹 → SKILL.md → 测试 → 注册
"""

import sys, json, tempfile, shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.creator import SkillCreator, CreationTask, CreationResult
from engine.bank import SkillBank
from engine.searcher import SkillSearcher

PASS = 0; FAIL = 0
def check(name, condition, detail=""):
    global PASS, FAIL
    if condition: PASS += 1; print(f"  ✅ {name}")
    else: FAIL += 1; print(f"  ❌ {name}  {detail}")
def section(title): print(f"\n{'='*50}\n  {title}\n{'='*50}")

# ── 准备临时 Skill Bank ──────────────────
tmp = tempfile.mkdtemp(prefix="c4_test_")
SKILLS_TMP = f"{tmp}/skills"

# ── 蒸馏函数：模拟从轨迹中生成技能产物 ──
# 在真实环境中，这个函数调用 Agent 推理。这里直接用硬编码产物验证 Creator 引擎。

def distill_fn(task: CreationTask) -> dict:
    """
    模拟蒸馏：从「MUSE 论文分析」对话轨迹中提取技能。
    真实场景：这个函数发 prompt 给 Agent，Agent 返回 JSON。
    """
    skill_md = """# 论文审查

## 目标
审查AI/技术论文的方法论、实验设计和结论，识别亮点、漏洞、未验证的假设，输出结构化批判分析。

## 适用场景
**正向触发：**
- 用户提供论文全文或详细摘要要求分析
- 用户要求「审这篇论文」「分析这篇文章」「论文有什么问题」
- 用户把写好的技术文章发来要求审查

**排除条件：**
- 论文语言非中文/英文
- 仅要求翻译或摘要，不做批判分析
- 非技术类论文（文学/历史等）

## 输入
- **论文文本** (必填)：论文全文或详细段落
- **关注维度** (可选)：方法论/实验/结论/创新性

## 输出
输出应包含：
1. 逐段/逐论点分析
2. 结构化批判（亮点/漏洞/未验证假设）
3. 改进建议
4. 总结判断

## 流程

### 步骤1：快速结构扫描
- 提取论文的核心论点、方法论、关键实验
- 检查点：已列出文献的骨架结构

### 步骤2：逐论点四维审查
1. **逻辑性**：推理链是否自洽
2. **实验支撑**：是否有数据/实验支撑
3. **覆盖范围**：结论的适用范围是否被恰当限定
4. **潜在漏洞**：是否存在循环论证、单轨迹偏差等

- 检查点：至少覆盖了四维中的三维

### 步骤3：亮点提取
- 识别真正有价值的创新点
- 区分「新范式」和「增量改进」

### 步骤4：漏洞标注
- 明确指出未经验证的假设
- 标注实验规模/覆盖度的限制

### 步骤5：生成改进建议
- 对每个漏洞给出具体的验证方案
- 区分「致命缺陷」和「可后续补充」

## 规则清单

### 方法论审查
- 【必须】检查实验数据是否能支撑结论（覆盖率/显著性/样本量）
- 【必须】区分论文自己承认的 limitation 和审稿人发现的隐藏漏洞
- 【禁止】不得仅凭论文自己声称的「state-of-the-art」就认可其领先性
- 【建议】对每个实验方案，追问反事实：如果原始条件变了，结论还成立吗

### 架构设计审查
- 【必须】检查是否存在自循环评测
- 【禁止】不得在没有独立复现的情况下声称「已被验证」
- 【建议】区分「工程创新」和「学术创新」

### 引用规范
- 【必须】引用原文具体段落作为证据
- 【禁止】使用「论文说」「作者认为」等模糊指代而不给出具体位置

## 已知失效模式

### 模式1：对作者自述的 limitation 过度信任
- 描述：只复述论文自己声称的局限，未发现作者未意识到的漏洞
- 对策：每个 limitation 追问「还有什么他们没说的？」

### 模式2：被实验数字震慑而不质疑方法论
- 描述：看到好看的表格就跳过对实验设计本身的审查
- 对策：先审方法论，再看数字

### 模式3：输出变成论文复述
- 描述：花费大量篇幅复述论文内容而非批判分析
- 对策：复述≤总篇幅的20%，用「论文认为→我们的判断」格式

## 参考
- 同行评审通用标准
- 实验可复现性检查清单
"""

    tests = [
        # 测试1：基本审查能力
        [
            "basic-review",
            """# case-001-basic-review: 基本审查能力

## 输入
```yaml
论文文本: "我们提出了一种新的Agent技能管理系统，包含五个阶段。在SkillsBench的51个任务上，系统在35个任务上生成了技能，准确率87.94%。"
关注维度: 方法论
```

## 期望输出检查

### 结构检查
- [ ] 出现了 "批判分析"
- [ ] 出现了 "亮点"
- [ ] 出现了 "漏洞"

### 内容检查
- [ ] 出现了 "覆盖率"
- [ ] 出现了 "实验规模"
"""
        ],
        # 测试2：不滥用验证词
        [
            "no-premature-validation",
            """# case-002-no-validation: 不使用无据断言

## 输入
```yaml
论文文本: "我们提出了一种新系统，实验表明其准确率超过人类基准。该发现已得到充分验证。"
关注维度: 实验
```

## 期望输出检查

### 边界检查
- [ ] "已被验证"出现次数 ≤ 0
- [ ] "充分验证"出现次数 ≤ 0

### 内容检查
- [ ] 出现了 "独立复现"
"""
        ],
    ]

    memory_md = """# 技能记忆：论文审查

## 有效经验

### 2026-06-11 [成功] 技能创建
- 场景：从MUSE论文分析对话中蒸馏
- 做法：提取逐论点四维审查法+亮点/漏洞二元结构
- 要点：批判分析不是复述——用"论文认为→我们的判断"格式
"""

    config = {
        "description": "审查AI/技术论文的方法论、实验设计和结论，输出结构化批判分析",
        "trigger_keywords": [
            "论文审查", "审论文", "分析论文", "论文分析",
            "review paper", "paper review", "论文有什么问题",
            "分析这篇文章", "批判分析"
        ],
        "tags": ["学术", "审查", "技术评估"],
    }

    return {
        "skill_md": skill_md,
        "tests": tests,
        "memory_md": memory_md,
        "config": config,
    }


# ── T1: 创建第二个技能 ──────────────────
section("T1: Creator 创建论文审查技能")

creator = SkillCreator(SKILLS_TMP, distillation_fn=distill_fn)

task = CreationTask(
    skill_name="论文审查",
    trace=(
        "用户发了MUSE论文的详细分析文章，我逐段审查并提出批判。"
        "识别了：单轨迹蒸馏风险、覆盖率瓶颈、实验规模限制、跨Agent迁移验证不足。"
        "区分了论文自己承认的limitation和我发现的隐藏漏洞。"
    ),
    success_input="论文文本: ...[MUSE论文全文]...",
    success_output="结构化批判：亮点X3 + 漏洞X4 + 改进建议X4",
    trigger_keywords=["论文审查", "审论文", "paper review", "分析论文"],
    tags=["学术", "审查"],
)

# 注入能覆盖断言词的 mock 输出函数
def mock_paper_review_output(skill_name: str, test_input: str) -> str:
    return (
        "## 批判分析\n\n"
        "### 亮点\n"
        "- 五阶段生命周期模型具有范式意义\n"
        "- 技能带测试的设计与软件工程理念对齐\n\n"
        "### 漏洞\n"
        "- 覆盖率不足：51个任务中仅35个成功生成技能（68.6%），16个任务完全无法进入蒸馏流程\n"
        "- 实验规模有限：每个任务仅5次运行，置信区间宽\n"
        "- 单轨迹蒸馏风险：hvac-control案例显示从80%跌至20%\n"
        "- 跨平台迁移仅验证了MUSE→Hermes单向\n\n"
        "### 改进建议\n"
        "- 对覆盖率为0的16个任务引入人机协同bootstrap\n"
        "- 增加多轨迹融合（ensemble distillation）降低脆弱性\n"
        "- 需要独立复现以确认结论的可迁移性\n"
    )

result = creator.create(task, test_output_fn=mock_paper_review_output)

print(f"  技能名: {result.skill_name}")
print(f"  注册状态: {'✅ 已注册' if result.registered else '❌ 未注册'}")
print(f"  测试: {result.tests_passed}/{result.tests_total}")
for line in result.report:
    print(f"    {line}")

check("技能创建成功且注册", result.registered)
check("测试全部通过", result.tests_passed == result.tests_total)

# ── T2: 验证文件写入 ──────────────────────
section("T2: 验证产物完整性")

skill_dir = Path(SKILLS_TMP) / "论文审查"
check("SKILL.md 存在", (skill_dir / "SKILL.md").exists())
check(".memory.md 存在", (skill_dir / ".memory.md").exists())
check("config.json 存在", (skill_dir / "config.json").exists())

tests_dir = skill_dir / "tests"
check("tests/ 目录存在", tests_dir.is_dir())
check("index.json 存在", (tests_dir / "index.json").exists())

case_files = list(tests_dir.glob("case-*.md"))
check(f"测试用例数 ≥ 2", len(case_files) >= 2, f"got {len(case_files)}")

# ── T3: 多技能检索验证 ───────────────────
section("T3: 双技能检索对比")

bank = SkillBank(SKILLS_TMP)
bank.scan_directory()
active = bank.list_active()
check("技能已注册在线", len(active) >= 1, f"got {len(active)}: {[s.name for s in active]}")

searcher = SkillSearcher(SKILLS_TMP)

# 论文任务→论文技能
r = searcher.search("帮我做论文审查", bank.index)
check("论文任务匹配论文技能", len(r) > 0 and r[0][0].name == "论文审查",
      f"top: {r[0][0].name if r else 'none'} (score: {r[0][2] if r else 0})")

# 合同任务→合同技能（不应错配）
# 这里只有论文审查，所以应该无匹配
r2 = searcher.search("帮我审一下这份合同", bank.index)
check("合同任务不误匹配论文技能", len(r2) == 0 or (
    len(r2) > 0 and r2[0][2] < 20  # 低分不算真命中
), f"top: {r2[0][0].name}, score: {r2[0][2]}" if r2 else "无匹配")

# 模糊任务→论文技能
r3 = searcher.search("分析一下这篇文章", bank.index)
check("中文口语任务命中论文技能", len(r3) > 0,
      f"got {len(r3)} matches")

# ── 总结 ──────────────────────────────────
print(f"\n{'='*50}")
print(f"  总计: {PASS + FAIL} 项")
print(f"  通过: {PASS}")
print(f"  失败: {FAIL}")
print(f"{'='*50}")

shutil.rmtree(tmp)

if FAIL > 0:
    print(f"\n⚠️  {FAIL} 项失败")
    sys.exit(1)
else:
    print("\n✅ C4 技能自动创建验证通过")

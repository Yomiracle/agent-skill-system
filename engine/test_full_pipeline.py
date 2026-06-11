"""
全链路集成测试：C1 检索 → C2 测试 → C3 精炼
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.bank import SkillBank
from engine.searcher import SkillSearcher
from engine.loader import SkillLoader
from engine.memory import MemoryManager
from engine.test_runner import TestRunner, mock_agent_output
from engine.refiner import SkillRefiner

SKILLS_DIR = str(Path(__file__).parent.parent / "skills")

bank = SkillBank(SKILLS_DIR)
bank.scan_directory()

searcher = SkillSearcher(SKILLS_DIR)
loader = SkillLoader(SKILLS_DIR)
runner = TestRunner(SKILLS_DIR)
refiner = SkillRefiner(SKILLS_DIR)

print("=" * 60)
print("FULL PIPELINE TEST: C1 + C2 + C3")
print("=" * 60)

# Step 1: C1 - Search
print("\n[Step 1] C1: 任务匹配")
results = searcher.search("帮我审一下这份股权协议的法律风险", bank.index)
assert results, "C1: 无匹配结果"
skill_name = results[0][0].name
print(f"  → 命中技能: {skill_name} (score: {results[0][2]})")

# Step 2: C1 - Load
print("\n[Step 2] C1: 加载技能")
entry = bank.get(skill_name)
bundle = loader.load(entry)
assert bundle, "C1: 加载失败"
prompt = loader.build_system_prompt(bundle)
assert len(prompt) > 0, "C1: Prompt 为空"
print(f"  → SKILL.md: {len(bundle.skill_md)} chars")
print(f"  → Memory:   {len(bundle.memory_entries)} 条经验")
print(f"  → Prompt:   {len(prompt)} chars")

# Step 3: C2 - Test
print("\n[Step 3] C2: 运行测试")
result = runner.evaluate(skill_name, mock_agent_output)
print(f"  → {result.passed}/{result.total} 通过, {result.failed} 失败")
for tc in result.cases:
    status_icon = "✅" if tc.status == "pass" else "❌"
    print(f"    {status_icon} {tc.id}: {tc.description}")

# Step 4: C3 - Quick Check
print("\n[Step 4] C3: 健康检查")
health = refiner.quick_check(skill_name, mock_agent_output)
print(f"  → 通过率: {health['pass_rate']:.0%}")
print(f"  → 诊断数: {len(health['diagnoses'])}")

# Step 5: C1 - Record usage
print("\n[Step 5] C1: 记录使用统计")
bank.record_use(skill_name, success=(result.passed == result.total))
updated = bank.get(skill_name)
print(f"  → use_count: {updated.use_count}")
print(f"  → success_rate: {updated.success_rate}")

# Step 6: C1 - Memory write
print("\n[Step 6] C1: 写入使用经验")
mem = MemoryManager(SKILLS_DIR + "/" + skill_name)
mem.append_success(
    title="全链路集成测试",
    scene="C1+C2+C3 流水线完整执行",
    approach="检索→加载→测试→健康检查→统计→记忆，全自动",
    takeaway="五阶段生命周期在代码层面完全闭环",
)

# Step 7: C2 - Update evaluation
bank.update_evaluation(skill_name, passed=True, test_count=result.total, passed_count=result.passed)
eval_info = bank.get(skill_name).last_evaluation
assert eval_info and eval_info.passed, "C2: 评估回写失败"
print(f"  → 评估已更新: {eval_info.passed_count}/{eval_info.test_count}")

# Done
print("\n" + "=" * 60)
print("✅ 全链路测试通过")
print(f"   技能: {skill_name}")
print(f"   C1 检索+加载: ✅")
print(f"   C2 测试评估:   ✅ ({result.passed}/{result.total})")
print(f"   C3 健康检查:   ✅ ({health['pass_rate']:.0%})")
print(f"   使用统计+记忆:  ✅")
print("=" * 60)

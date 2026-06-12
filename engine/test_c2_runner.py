"""
C2 测试执行器验证
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.test_runner import TestRunner, TestParser, mock_agent_output
from engine.bank import SkillBank

SKILLS_DIR = str(Path(__file__).parent.parent / "skills")
PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}  {detail}")

def section(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")

# ── T1: 测试文件解析 ──────────────────────
section("T1: 测试用例文件解析")

tests_dir = Path(SKILLS_DIR) / "__test_skill__" / "tests"
cases = []

for f in sorted(tests_dir.glob("case-*.md")):
    tc = TestParser.parse_case(f)
    cases.append(tc)
    print(f"\n  [{tc.id}] {tc.description}")
    print(f"    输入长度: {len(tc.input_yaml)} 字符")
    print(f"    断言数量: {len(tc.checks)}")
    for c in tc.checks:
        print(f"      [{c.category}] {c.text[:60]}...")

check("解析3个用例", len(cases) == 3, f"got {len(cases)}")
check("case-001-basic 有断言", len(cases[0].checks) > 0)
check("case-002 有边界断言",
      any("边界" in ck.category for ck in cases[1].checks))

# ── T2: 测试执行全流程 ──────────────────
section("T2: 执行测试（mock agent）")

runner = TestRunner(SKILLS_DIR)
# rename mock_agent_output to output_fn to avoid name collision
output_fn = mock_agent_output

result = runner.evaluate("__test_skill__", output_fn)

print(f"\n  技能: {result.skill_name}")
print(f"  总计: {result.total}")
print(f"  通过: {result.passed}")
print(f"  失败: {result.failed}")

for tc in result.cases:
    print(f"\n  [{tc.status}] {tc.id}: {tc.description}")
    for ck in tc.checks:
        icon = "✅" if ck.passed else "❌"
        print(f"    {icon} [{ck.category}] {ck.text[:80]}")

check("3个用例全部执行", result.total == 3)
check("至少2个 pass", result.passed >= 2, f"passed={result.passed}")

# ── T3: 断言引擎专项 ──────────────────────
section("T3: 断言引擎专项验证")

from engine.test_runner import CheckItem

# 3.1 词频检查
ck = CheckItem(category="边界", text='"24%"出现次数 ≤ 1')
# 输出出现2次24%，断言≤1 → 应失败
runner._check_assertion(ck, "24%只是一个历史数字，现在用LPR四倍，24%不再用")
check("词频2次断言≤1→应被挡", not ck.passed, f"got ck.passed={ck.passed}")

ck2 = CheckItem(category="边界", text='"24%"出现次数 ≤ 1')
runner._check_assertion(ck2, "用LPR四倍就可以了")
check("词频0次断言≤1→通过", ck2.passed)

# 3.2 禁止出现
ck3 = CheckItem(category="边界", text='未使用 "民间借贷利率保护上限"')
runner._check_assertion(ck3, "违约金按民法典585条处理")
check("禁止词不出现→pass", ck3.passed)

ck4 = CheckItem(category="边界", text='未使用 "民间借贷利率保护上限"')
runner._check_assertion(ck4, "参考民间借贷利率保护上限")
check("禁止词出现→fail", not ck4.passed)

# 3.3 出现检查
ck5 = CheckItem(category="内容", text='出现了 "《民法典》第585条"')
runner._check_assertion(ck5, "依据《民法典》第585条，违约金...")
check("出现检查 pass", ck5.passed)

ck6 = CheckItem(category="内容", text='出现了 "《民法典》第585条"')
runner._check_assertion(ck6, "依据民法典有关规定...")
check("出现检查 fail(无匹配)", not ck6.passed)

# 3.4 以下之一
ck7 = CheckItem(category="内容", text='至少出现了以下之一：《民法典》第585条、LPR四倍')
runner._check_assertion(ck7, "建议用LPR四倍标准")
check("以下之一 pass(命中第2个)", ck7.passed)

ck8 = CheckItem(category="内容", text='至少出现了以下之一：《民法典》第585条、LPR四倍')
runner._check_assertion(ck8, "违约金过高会被调低")
check("以下之一 fail(都不命中)", not ck8.passed)

# ── T4: 与 SkillBank 联动 ────────────────
section("T4: 评估结果回写 SkillBank")

bank = SkillBank(SKILLS_DIR)
bank.load_index()
bank.update_evaluation("__test_skill__", passed=True, test_count=3, passed_count=3)

entry = bank.get("__test_skill__")
check("评估结果已写入", entry.last_evaluation is not None and entry.last_evaluation.passed)

# ── 总结 ──────────────────────────────────
print(f"\n{'='*50}")
print(f"  总计: {PASS + FAIL} 项")
print(f"  通过: {PASS}")
print(f"  失败: {FAIL}")
print(f"{'='*50}")

if FAIL > 0:
    print(f"\n⚠️  {FAIL} 项失败")
    sys.exit(1)
else:
    print("\n✅ C2 测试执行器验证通过")

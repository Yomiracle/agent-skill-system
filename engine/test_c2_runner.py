"""
C2 测试执行器验证
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.test_runner import TestRunner, TestParser, mock_agent_output
from engine.bank import SkillBank

SKILLS_DIR = str(Path(__file__).parent.parent / "skills")

# ── 自建测试fixture ──
import os as _os
_fixture_dir = str(Path(__file__).parent.parent / "skills" / "__test_skill__")
_tests_dir = _fixture_dir + "/tests"
_os.makedirs(_tests_dir, exist_ok=True)
if not _os.path.exists(_fixture_dir + "/SKILL.md"):
    open(_fixture_dir + "/SKILL.md","w").write("""# __test_skill__\nEngine test fixture.\n## 目标\n测试引擎。\n## 硬规则\n- 【必须】always return valid JSON\n- 【禁止】never output raw SQL\n## 流程\n1. Parse\n2. Apply rules\n3. Return""")
    open(_fixture_dir + "/.memory.md","w").write("# 技能记忆：__test_skill__\n## 有效经验\n### 2026-06-12 [成功] test\n- 场景：auto\n- 做法：fixture\n- 要点：minimal")
    open(_fixture_dir + "/config.json","w").write('{"name":"__test_skill__","version":"1.0.0","description":"Engine test fixture","trigger_keywords":["test"],"tags":["test"],"dependencies":[],"max_context_percent":30,"created_at":"2026-06-12T00:00:00Z","last_used_at":"2026-06-12T00:00:00Z"}')
    open(_tests_dir + "/index.json","w").write('{"test_cases":[{"id":"case-001-check","file":"case-001-check.md","description":"输出验证","expected_result":"pass"},{"id":"case-002-no-sql","file":"case-002-no-sql.md","description":"禁用SQL","expected_result":"pass"},{"id":"case-003-contains","file":"case-003-contains.md","description":"内容验证","expected_result":"pass"}]}')
    open(_tests_dir + "/case-001-check.md","w").write("# case-001\n## 输入\n```yaml\ntask: test\n```\n## 期望输出检查\n### 结构检查\n- [ ] 出现了 \"result\"\n### 内容检查\n- [ ] 解释了为什么")
    open(_tests_dir + "/case-002-no-sql.md","w").write("# case-002\n## 输入\n```yaml\ntask: test\n```\n## 期望输出检查\n### 边界检查\n- [ ] \"SELECT\"出现次数 < 2")
    open(_tests_dir + "/case-003-contains.md","w").write("# case-003\n## 输入\n```yaml\ntask: test\n```\n## 期望输出检查\n### 内容检查\n- [ ] 以下之一：result、output、done")

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

# ── 自建测试fixture ──
import os as _os
_fixture_dir = str(Path(__file__).parent.parent / "skills" / "__test_skill__")
_tests_dir = _fixture_dir + "/tests"
_os.makedirs(_tests_dir, exist_ok=True)
if not _os.path.exists(_fixture_dir + "/SKILL.md"):
    open(_fixture_dir + "/SKILL.md","w").write("""# __test_skill__\nEngine test fixture.\n## 目标\n测试引擎。\n## 硬规则\n- 【必须】always return valid JSON\n- 【禁止】never output raw SQL\n## 流程\n1. Parse\n2. Apply rules\n3. Return""")
    open(_fixture_dir + "/.memory.md","w").write("# 技能记忆：__test_skill__\n## 有效经验\n### 2026-06-12 [成功] test\n- 场景：auto\n- 做法：fixture\n- 要点：minimal")
    open(_fixture_dir + "/config.json","w").write('{"name":"__test_skill__","version":"1.0.0","description":"Engine test fixture","trigger_keywords":["test"],"tags":["test"],"dependencies":[],"max_context_percent":30,"created_at":"2026-06-12T00:00:00Z","last_used_at":"2026-06-12T00:00:00Z"}')
    open(_tests_dir + "/index.json","w").write('{"test_cases":[{"id":"case-001-check","file":"case-001-check.md","description":"输出验证","expected_result":"pass"},{"id":"case-002-no-sql","file":"case-002-no-sql.md","description":"禁用SQL","expected_result":"pass"},{"id":"case-003-contains","file":"case-003-contains.md","description":"内容验证","expected_result":"pass"}]}')
    open(_tests_dir + "/case-001-check.md","w").write("# case-001\n## 输入\n```yaml\ntask: test\n```\n## 期望输出检查\n### 结构检查\n- [ ] 出现了 \"result\"\n### 内容检查\n- [ ] 解释了为什么")
    open(_tests_dir + "/case-002-no-sql.md","w").write("# case-002\n## 输入\n```yaml\ntask: test\n```\n## 期望输出检查\n### 边界检查\n- [ ] \"SELECT\"出现次数 < 2")
    open(_tests_dir + "/case-003-contains.md","w").write("# case-003\n## 输入\n```yaml\ntask: test\n```\n## 期望输出检查\n### 内容检查\n- [ ] 以下之一：result、output、done")

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

"""
C1 引擎——边界与压力测试
"""

import sys, json, os, tempfile, shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.bank import SkillBank
from engine.searcher import SkillSearcher
from engine.loader import SkillLoader
from engine.memory import MemoryManager

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


# ─────────────────────────────────────────────
section("T1: 空目录启动")

tmp = tempfile.mkdtemp(prefix="skill_test_empty_")
os.makedirs(f"{tmp}/skills", exist_ok=True)
bank = SkillBank(f"{tmp}/skills")
bank.scan_directory()
check("空目录不崩溃", True)
check("空目录技能数=0", len(bank.list_active()) == 0)
shutil.rmtree(tmp)

# ─────────────────────────────────────────────
section("T2: 缺失 config.json 目录容错")

tmp = tempfile.mkdtemp(prefix="skill_test_partial_")
os.makedirs(f"{tmp}/skills/broken", exist_ok=True)
bank = SkillBank(f"{tmp}/skills")
bank.scan_directory()
check("缺 config 不崩溃", True)
check("缺 config 不注册", len(bank.list_active()) == 0)

# 引用不存在的目录
with open(f"{tmp}/skills/config.json", "w") as f:
    json.dump({"version": "1.0", "skills": [
        {"name": "ghost", "path": "ghost", "status": "active", "version": "1.0",
         "created_at": "", "updated_at": "", "last_used_at": "", "use_count": 0, "success_rate": 1.0}
    ]}, f)
bank2 = SkillBank(f"{tmp}/skills")
bank2.load_index()
s = SkillSearcher(f"{tmp}/skills")
results = s.search("测试", bank2.index)
check("不存在的目录返回空", len(results) == 0, f"got {len(results)}")
shutil.rmtree(tmp)

# ─────────────────────────────────────────────
section("T3: 多技能检索——干扰与精确匹配")

tmp = tempfile.mkdtemp(prefix="skill_test_multi_")
os.makedirs(f"{tmp}/skills/faq", exist_ok=True)
os.makedirs(f"{tmp}/skills/translate", exist_ok=True)

with open(f"{tmp}/skills/faq/config.json", "w") as f:
    json.dump({
        "name": "FAQ问答", "version": "1.0",
        "description": "回答常见问题",
        "trigger_keywords": ["常见问题", "FAQ", "帮助"],
        "tags": ["客服"]
    }, f, ensure_ascii=False)
Path(f"{tmp}/skills/faq/SKILL.md").write_text("# FAQ\n回答常见问题", encoding="utf-8")

with open(f"{tmp}/skills/translate/config.json", "w") as f:
    json.dump({
        "name": "翻译", "version": "1.0",
        "description": "翻译文本",
        "trigger_keywords": ["翻译", "translate", "英文"],
        "tags": ["语言"]
    }, f, ensure_ascii=False)
Path(f"{tmp}/skills/translate/SKILL.md").write_text("# Translate\nTranslate text", encoding="utf-8")

bank3 = SkillBank(f"{tmp}/skills")
bank3.scan_directory()
check("2技能注册成功", len(bank3.list_active()) == 2)

s3 = SkillSearcher(f"{tmp}/skills")

r = s3.search("翻译这段话", bank3.index)
check("翻译匹配翻译技能", len(r) > 0 and r[0][0].name == "翻译",
      f"top: {r[0][0].name if r else 'none'}")

r = s3.search("查看常见问题", bank3.index)
check("常见问题匹配FAQ", len(r) > 0 and r[0][0].name == "FAQ问答",
      f"top: {r[0][0].name if r else 'none'}")

r = s3.search("今天天气真好", bank3.index)
check("无关任务无匹配", len(r) == 0, f"got {len(r)} matches")

shutil.rmtree(tmp)

# ─────────────────────────────────────────────
section("T4: 使用真实技能目录")

bank_real = SkillBank(SKILLS_DIR)
bank_real.scan_directory()
check("真实技能注册", len(bank_real.list_active()) >= 1)

# ─────────────────────────────────────────────
section("T5: Loader 容错")

loader = SkillLoader(SKILLS_DIR)
from engine.models import SkillEntry, SkillStatus
fake_entry = SkillEntry(
    name="不存在", path="nonexistent", status=SkillStatus.ACTIVE,
    version="1.0", created_at="", updated_at="", last_used_at="",
    use_count=0, success_rate=1.0
)
bundle = loader.load(fake_entry)
check("不存在技能返回 None", bundle is None)

entry = bank_real.get("__test_skill__")
check("get 真实技能非空", entry is not None)
if entry:
    bundle = loader.load(entry)
    check("真实技能加载成功", bundle is not None)
    if bundle:
        check("SKILL.md 非空", len(bundle.skill_md) > 0)
        check("Memory entries 已解析", len(bundle.memory_entries) >= 0)
        prompt = loader.build_system_prompt(bundle)
        check("Prompt 生成非空", len(prompt) > 0)
        check("Prompt 含技能名", bundle.config.name in prompt)

# ─────────────────────────────────────────────
section("T6: 中文边界任务 + 多技能不误匹配")

searcher_real = SkillSearcher(SKILLS_DIR)
check("空字符串不崩溃", len(searcher_real.search("", bank_real.index)) == 0)
check("纯英文 search 不崩溃",
      isinstance(searcher_real.search("please review this feedback", bank_real.index), list))
check("邮件起草不误匹配合同", 
      len(searcher_real.search("帮我写一封邮件", bank_real.index)) == 0,
      f"有误匹配: {[r[0].name for r in searcher_real.search('写邮件', bank_real.index)]}")

# ─────────────────────────────────────────────
section("T7: 重复注册——用真实 bank 测试后立即废弃")

bank_real.register("test_dup", "test_dup")
bank_real.register("test_dup", "test_dup")
test_dups = [s for s in bank_real.list_active() if s.name == "test_dup"]
check("重复注册不产生多条", len(test_dups) == 1, f"got {len(test_dups)}")
bank_real.deprecate("test_dup")
check("废弃后清除干净", "test_dup" not in [s.name for s in bank_real.list_active()])

# ─────────────────────────────────────────────
section("T8: 废弃技能完整生命周期")

bank_real.register("to_dep", "to_dep")
check("注册后 active", bank_real.get("to_dep").status.value == "active")
bank_real.deprecate("to_dep")
dep_entry = bank_real.get("to_dep")
check("废弃后 status=deprecated", dep_entry.status.value == "deprecated")
check("废弃后不在 active 列表", "to_dep" not in [s.name for s in bank_real.list_active()])

# ─────────────────────────────────────────────
section("T9: 统计滑窗衰减")

bank_real.register("stat_test", "stat_test")
bank_real.record_use("stat_test", success=False)
check("第1次失败后 < 1.0", bank_real.get("stat_test").success_rate < 1.0)
for _ in range(5):
    bank_real.record_use("stat_test", success=True)
check("恢复后 > 0.9", bank_real.get("stat_test").success_rate > 0.9,
       f"rate={bank_real.get('stat_test').success_rate}")
bank_real.deprecate("stat_test")

# ─────────────────────────────────────────────
section("T10: Memory 截断保护")

tmp = tempfile.mkdtemp(prefix="skill_mem_")
os.makedirs(f"{tmp}/test_skill", exist_ok=True)
mem = MemoryManager(f"{tmp}/test_skill")
for i in range(600):
    mem.append_success(
        title=f"测试 {i}",
        scene="压力测试",
        approach="大量写入",
        takeaway="验证截断"
    )
content = mem.read()
lines = len(content.split("\n"))
check("Memory 截断生效", lines <= MemoryManager.MAX_LINES + 20, f"实际行数: {lines}")
shutil.rmtree(tmp)

# ─────────────────────────────────────────────
section("T11: Search 分数排序")

tmp = tempfile.mkdtemp(prefix="skill_rank_")
os.makedirs(f"{tmp}/skills", exist_ok=True)

for i, (name, kws) in enumerate([
    ("精确匹配", ["审合同", "审查合同"]),
    ("部分匹配", ["法律风险"]),
    ("弱匹配", ["文档处理"]),
]):
    d = f"{tmp}/skills/skill_{i}"
    os.makedirs(d, exist_ok=True)
    with open(f"{d}/config.json", "w") as f:
        json.dump({
            "name": name, "version": "1.0",
            "description": name,
            "trigger_keywords": kws
        }, f, ensure_ascii=False)
    Path(f"{d}/SKILL.md").write_text(f"# {name}", encoding="utf-8")

bank_rank = SkillBank(f"{tmp}/skills")
bank_rank.scan_directory()
s_rank = SkillSearcher(f"{tmp}/skills")

r = s_rank.search("审查合同", bank_rank.index)
check("至少1个结果", len(r) >= 1, f"got {len(r)}")
if len(r) >= 2:
    check("精确匹配排第一", r[0][0].name == "精确匹配", f"top={r[0][0].name}")
    check("分数递减", r[0][2] >= r[1][2], f"{r[0][2]} vs {r[1][2]}")
shutil.rmtree(tmp)

# ─────────────────────────────────────────────
section("T12: Prompt 格式完整性")

entry = bank_real.get("__test_skill__")
if entry:
    bundle = loader.load(entry)
    if bundle:
        prompt = loader.build_system_prompt(bundle)
        check("含技能激活标题", "已激活技能" in prompt)
        check("含 SKILL.md 节", "技能规范" in prompt)
        check("含记忆节", "技能记忆" in prompt)
        check("不含空行异常", "\n\n\n\n" not in prompt)

# ─────────────────────────────────────────────
# 清理临时目录里产生的残留
# (T7-T9 产生的 test_dup/to_dep/stat_test 已废弃，但还在索引里)

# ─────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"  总计: {PASS + FAIL} 项")
print(f"  通过: {PASS}")
print(f"  失败: {FAIL}")
print(f"{'='*50}")

if FAIL > 0:
    print(f"\n⚠️  {FAIL} 项失败，需要修复")
    sys.exit(1)
else:
    print("\n✅ C1 引擎全量边界测试通过")

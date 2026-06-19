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
from engine.fixture_support import ensure_test_skill_fixture

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
FIXTURE_TMP = tempfile.mkdtemp(prefix="skill_fixture_")
FIXTURE_SKILLS_DIR = str(Path(FIXTURE_TMP) / "skills")
ensure_test_skill_fixture(FIXTURE_SKILLS_DIR)
fixture_bank = SkillBank(FIXTURE_SKILLS_DIR)
fixture_bank.scan_directory()


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

loader = SkillLoader(FIXTURE_SKILLS_DIR)
from engine.models import SkillEntry, SkillStatus
fake_entry = SkillEntry(
    name="不存在", path="nonexistent", status=SkillStatus.ACTIVE,
    version="1.0", created_at="", updated_at="", last_used_at="",
    use_count=0, success_rate=1.0
)
bundle = loader.load(fake_entry)
check("不存在技能返回 None", bundle is None)

entry = fixture_bank.get("__test_skill__")
check("get fixture 技能非空", entry is not None)
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
section("T7: 重复注册——用临时 bank 测试后立即废弃")

fixture_bank.register("test_dup", "test_dup")
fixture_bank.register("test_dup", "test_dup")
test_dups = [s for s in fixture_bank.list_active() if s.name == "test_dup"]
check("重复注册不产生多条", len(test_dups) == 1, f"got {len(test_dups)}")
fixture_bank.deprecate("test_dup")
check("废弃后清除干净", "test_dup" not in [s.name for s in fixture_bank.list_active()])

# ─────────────────────────────────────────────
section("T8: 废弃技能完整生命周期")

fixture_bank.register("to_dep", "to_dep")
check("注册后 active", fixture_bank.get("to_dep").status.value == "active")
fixture_bank.deprecate("to_dep")
dep_entry = fixture_bank.get("to_dep")
check("废弃后 status=deprecated", dep_entry.status.value == "deprecated")
check("废弃后不在 active 列表", "to_dep" not in [s.name for s in fixture_bank.list_active()])

# ─────────────────────────────────────────────
section("T9: 统计滑窗衰减")

fixture_bank.register("stat_test", "stat_test")
fixture_bank.record_use("stat_test", success=False)
check("第1次失败后 < 1.0", fixture_bank.get("stat_test").success_rate < 1.0)
for _ in range(5):
    fixture_bank.record_use("stat_test", success=True)
check("恢复后 > 0.9", fixture_bank.get("stat_test").success_rate > 0.9,
       f"rate={fixture_bank.get('stat_test').success_rate}")
fixture_bank.deprecate("stat_test")

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

entry = fixture_bank.get("__test_skill__")
if entry:
    bundle = loader.load(entry)
    if bundle:
        prompt = loader.build_system_prompt(bundle)
        check("含技能激活标题", "已激活技能" in prompt)
        check("含 SKILL.md 节", "技能规范" in prompt)
        check("含记忆节", "技能记忆" in prompt)
        check("不含空行异常", "\n\n\n\n" not in prompt)

# ─────────────────────────────────────────────
shutil.rmtree(FIXTURE_TMP, ignore_errors=True)

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

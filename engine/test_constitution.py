import sys, re
from pathlib import Path

SKILLS_DIR = str(Path(__file__).parent.parent / "skills")
PASS = FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition: PASS += 1; print(f"  ✅ {name}")
    else: FAIL += 1; print(f"  ❌ {name}  {detail}")

def section(title): print(f"\n{'='*50}\n  {title}\n{'='*50}")

section("C1: .memory.md 根因不能是粗心等")
for sp in Path(SKILLS_DIR).iterdir():
    if not sp.is_dir() or sp.name.startswith(".") or sp.name.startswith("__"): continue
    mf = sp / ".memory.md"
    if not mf.exists(): continue
    content = mf.read_text(encoding="utf-8")
    for w in ["粗心","疏忽","没注意到","忘了","不小心","大意"]:
        bad = False; idx = content.find(w)
        if idx >= 0 and "根因" in content[max(0,idx-30):idx+30]: bad = True
        check(f"{sp.name}: 不含'{w}'作根因", not bad)

section("C2: SKILL.md 原子性")
for sp in Path(SKILLS_DIR).iterdir():
    if not sp.is_dir() or sp.name.startswith(".") or sp.name.startswith("__"): continue
    md = sp / "SKILL.md"
    if not md.exists(): continue
    t = md.read_text(encoding="utf-8")
    gm = re.search(r'##\s*目标\s*\n(.*?)(?=\n##|\Z)', t, re.DOTALL)
    gl = gm.group(1).strip().split('\n') if gm else []
    gl = [l for l in gl if l.strip() and not l.strip().startswith('>')]
    fm = re.search(r'##\s*流程\s*\n(.*?)(?=\n##|\Z)', t, re.DOTALL)
    fs = len(re.findall(r'(?:^|\n)\s*\d+\.', fm.group(1) if fm else ""))
    check(f"{sp.name}: 目标≤2句 (当前{len(gl)}句)", len(gl) <= 2)
    check(f"{sp.name}: 流程≤10步 (当前{fs}步)", fs <= 10, ">10步建议拆分")

section("C3: refiner.py 精炼记录可追溯")
rc = Path(__file__).parent.joinpath("refiner.py").read_text(encoding="utf-8")
check("refiner.py 包含 changelog", "changelog" in rc.lower())

section("C4: SKILL.md 未将答辩状列为正例")
for sp in Path(SKILLS_DIR).iterdir():
    if not sp.is_dir() or sp.name.startswith(".") or sp.name.startswith("__"): continue
    md = sp / "SKILL.md"
    if not md.exists(): continue
    t = md.read_text(encoding="utf-8")
    bad = False; idx = 0
    while True:
        idx = t.find("答辩状", idx)
        if idx == -1: break
        ctx = t[max(0,idx-40):idx+40]
        not_negative = True
        for w in ["禁止","不可","❌","排除","不能","不应","失效","已知失","诉讼行为","不属于"]:
            if w in ctx: not_negative = False; break
        if not_negative: bad = True; break
        idx += 1
    check(f"{sp.name}: 答辩状不在正例中", not bad)

print(f"\n{'='*50}\n  Constitution: {PASS}/{PASS+FAIL} 通过\n{'='*50}")
if FAIL: sys.exit(1)

#!/usr/bin/env python3
"""
Skill Engine CLI - command-line interface for skill management.

Usage:
  python3 engine/cli.py list                          # list all skills
  python3 engine/cli.py search "review contract"      # search matching skills
  python3 engine/cli.py load "contract-review"        # load skill -> stdout
  python3 engine/cli.py memory "skill" success ...    # append memory entry
  python3 engine/cli.py test -m "skill"               # run tests (mock mode)
  python3 engine/cli.py health "skill"                # quick health check
  python3 engine/cli.py stats "skill" [-r]            # show/sync usage stats
"""

import sys, json
from pathlib import Path

ENGINE_ROOT = Path(__file__).parent.parent
SKILLS_DIR = str(ENGINE_ROOT / "skills")
sys.path.insert(0, str(ENGINE_ROOT))

from engine.bank import SkillBank
from engine.searcher import SkillSearcher
from engine.loader import SkillLoader
from engine.memory import MemoryManager
from engine.test_runner import TestRunner, mock_agent_output
from engine.refiner import SkillRefiner


# ── generic mock output ──
def generic_mock(skill_name, input_yaml):
    if "合同" in skill_name or "证据" in skill_name or "__test" in skill_name:
        return mock_agent_output(skill_name, input_yaml)
    if "论文" in skill_name:
        return "## 批判分析\n\n### 亮点\n- 创新点\n\n### 漏洞\n- 覆盖率不足\n- 实验规模有限\n\n### 改进建议\n- 需要独立复现"
    if "Bug" in skill_name or "bug" in skill_name.lower():
        return (
            "## 错误分类：语法错误\n"
            "## 根因定位：第3行 keyword_hits 未初始化\n"
            "## 修复方案：在第2行添加 keyword_hits = 0\n"
            "## 验证：python3 engine/test_xxx.py\n\n"
            "已知模式：AttributeError - CheckItem 是 dataclass 不是 dict，"
            "应用 .text 属性而非 .get() 方法。错误行号：cli.py 165。"
        )
    return "analysis coverage limitation review evaluation"


def cmd_list(bank):
    active = bank.list_active()
    if not active:
        print("(empty)")
        return
    print(f"{'Skill':<20} {'Ver':<8} {'Used':<6} {'Succ%':<8} {'Tests':<10}")
    print("-" * 60)
    for s in active:
        tests = f"{s.last_evaluation.passed_count}/{s.last_evaluation.test_count}" if s.last_evaluation else "N/A"
        print(f"{s.name:<20} {s.version:<8} {s.use_count:<6} {s.success_rate:<8.2f} {tests:<10}")


def cmd_search(searcher, bank, task):
    results = searcher.search(task, bank.index, top_n=3)
    if not results:
        print("(no match)")
        return 1
    for entry, cfg, score in results:
        print(f"[{score:.0f}] {entry.name} - {cfg.description[:60]}")
        kw_hits = [kw for kw in cfg.trigger_keywords if kw.lower() in task.lower()]
        print(f"    keywords: {', '.join(kw_hits[:4]) if kw_hits else 'partial match'}")
    return 0


def cmd_load(loader, bank, skill_name):
    entry = bank.get(skill_name)
    if not entry:
        print(f"skill not found: {skill_name}", file=sys.stderr)
        return 1
    bundle = loader.load(entry)
    if not bundle:
        print(f"load failed: {skill_name}", file=sys.stderr)
        return 1
    prompt = loader.build_system_prompt(bundle)
    print(prompt)
    return 0


def cmd_memory(bank, args):
    if len(args) < 3:
        print("usage: memory <skill_name> <success|failure|correction> <title> ...", file=sys.stderr)
        return 1
    skill_name = args[0]; mtype = args[1]
    entry = bank.get(skill_name)
    if not entry:
        print(f"skill not found: {skill_name}", file=sys.stderr); return 1
    mem = MemoryManager(SKILLS_DIR + "/" + entry.path)

    if mtype == "success":
        if len(args) < 6:
            print("usage: memory <name> success <title> <scene> <approach> <takeaway>", file=sys.stderr); return 1
        mem.append_success(title=args[2], scene=args[3], approach=args[4], takeaway=args[5])
    elif mtype == "failure":
        if len(args) < 7:
            print("usage: memory <name> failure <title> <scene> <error> <root_cause> <fix>", file=sys.stderr); return 1
        mem.append_failure(title=args[2], scene=args[3], error=args[4], root_cause=args[5], fix=args[6])
    elif mtype == "correction":
        if len(args) < 6:
            print("usage: memory <name> correction <title> <overwrites> <reason> <new_rule>", file=sys.stderr); return 1
        mem.append_correction(title=args[2], overwrites=args[3], reason=args[4], new_rule=args[5])
    else:
        print(f"unknown type: {mtype}", file=sys.stderr); return 1

    print(f"[{skill_name}] {mtype} recorded: {args[2]}")
    return 0


def cmd_test(use_mock, bank, skill_name):
    runner = TestRunner(SKILLS_DIR)
    entry = bank.get(skill_name)
    if not entry:
        print(f"skill not found: {skill_name}", file=sys.stderr); return 1

    def output_fn(s, i):
        return generic_mock(s, i)

    result = runner.evaluate(skill_name, output_fn)
    print(f"Skill: {skill_name}  {result.passed}/{result.total} passed  {result.failed} failed\n")
    for tc in result.cases:
        icon = "PASS" if tc.status == "pass" else ("FAIL" if tc.status == "fail" else "ERR")
        print(f"  [{icon}] {tc.id}: {tc.description}")
        if tc.status == "fail":
            for ck in tc.checks:
                if ck.passed is False:
                    print(f"    X [{ck.category}] {ck.text[:80]}")
    bank.update_evaluation(skill_name,
                           passed=(result.passed == result.total),
                           test_count=result.total, passed_count=result.passed)
    return 0 if result.passed == result.total else 1


def cmd_health(bank, skill_name):
    refiner = SkillRefiner(SKILLS_DIR)
    h = refiner.quick_check(skill_name, generic_mock)
    print(f"Skill: {skill_name}")
    print(f"Pass rate: {h['pass_rate']:.0%} ({h['passed']}/{h['total']})")
    if h.get('diagnoses'):
        print(f"Diagnoses: {len(h['diagnoses'])}")
        for d in h['diagnoses'][:5]:
            cat = d.get('category', '?')
            ck = d.get('check', None)
            txt = ck if isinstance(ck, str) else (ck.text if hasattr(ck, 'text') else str(ck))
            print(f"  [{cat}] {txt[:60]}")


def cmd_stats(bank, skill_name, record=False):
    entry = bank.get(skill_name)
    if not entry:
        print(f"skill not found: {skill_name}"); return 1
    print(f"Skill: {skill_name}")
    print(f"  Version:      {entry.version}")
    print(f"  Status:       {entry.status.value}")
    print(f"  Use count:    {entry.use_count}")
    print(f"  Success rate: {entry.success_rate:.2f}")
    print(f"  Last used:    {entry.last_used_at}")
    if entry.last_evaluation:
        print(f"  Last test:    {entry.last_evaluation.passed_count}/{entry.last_evaluation.test_count}")
    if record:
        bank.record_use(skill_name, success=True)
        print(f"  -> recorded 1 use")


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]; args = sys.argv[2:]
    bank = SkillBank(SKILLS_DIR); bank.scan_directory()

    if cmd == "list":
        cmd_list(bank)
    elif cmd == "search":
        if not args: print("usage: search <description>", file=sys.stderr); sys.exit(1)
        searcher = SkillSearcher(SKILLS_DIR)
        sys.exit(cmd_search(searcher, bank, " ".join(args)))
    elif cmd == "load":
        if not args: print("usage: load <skill_name>", file=sys.stderr); sys.exit(1)
        loader = SkillLoader(SKILLS_DIR)
        sys.exit(cmd_load(loader, bank, args[0]))
    elif cmd == "memory":
        sys.exit(cmd_memory(bank, args))
    elif cmd == "test":
        use_mock = "-m" in args
        args_clean = [a for a in args if a != "-m"]
        if not args_clean: print("usage: test [-m] <skill_name>", file=sys.stderr); sys.exit(1)
        sys.exit(cmd_test(use_mock, bank, args_clean[0]))
    elif cmd == "health":
        if not args: print("usage: health <skill_name>", file=sys.stderr); sys.exit(1)
        cmd_health(bank, args[0])
    elif cmd == "stats":
        if not args: print("usage: stats <skill_name>", file=sys.stderr); sys.exit(1)
        cmd_stats(bank, args[0], record=("-r" in args))
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        print(__doc__); sys.exit(1)


if __name__ == "__main__":
    main()

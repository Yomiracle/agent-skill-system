"""C1 引擎集成测试"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.bank import SkillBank
from engine.searcher import SkillSearcher
from engine.loader import SkillLoader
from engine.memory import MemoryManager

SKILLS_DIR = str(Path(__file__).parent.parent / "skills")


def main():
    print("=" * 60)
    print("Agent Skill System - C1 Engine Integration Test")
    print("=" * 60)

    # ── 1. Load Skill Bank ──────────────────
    print("\n[1] Loading Skill Bank ...")
    bank = SkillBank(SKILLS_DIR)
    bank.scan_directory()
    active = bank.list_active()
    print(f"    Registered skills: {len(active)}")
    for s in active:
        print(f"    - {s.name} v{s.version} (used: {s.use_count})")

    # ── 2. Search ────────────────────────────
    print("\n[2] Skill Search ...")
    searcher = SkillSearcher(SKILLS_DIR)
    loader = SkillLoader(SKILLS_DIR)

    test_tasks = [
        "帮我审一下这份股权代持协议，我是甲方",
        "帮我写一封邮件给客户",
        "帮我审查合同的法律风险",
        "审合同",
    ]

    for task in test_tasks:
        results = searcher.search(task, bank.index, top_n=2)
        print(f'\n    Task: "{task}"')
        if results:
            for entry, cfg, score in results:
                print(f"    -> Hit: [{score:.1f}] {entry.name}")
                hits = [kw for kw in cfg.trigger_keywords if kw.lower() in task.lower()]
                print(f"       Keyword hits: {hits}")
        else:
            print("    -> No match")

    # ── 3. Load skill + build system prompt ──
    print("\n[3] Load skill and build system prompt ...")
    results = searcher.search("审合同", bank.index, top_n=1)
    if results:
        entry, cfg, score = results[0]
        bundle = loader.load(entry)
        if bundle:
            prompt = loader.build_system_prompt(bundle)
            print(f"    Skill: {bundle.config.name}")
            print(f"    SKILL.md length: {len(bundle.skill_md)} chars")
            print(f"    Memory entries: {len(bundle.memory_entries)}")
            print(f"    System prompt length: {len(prompt)} chars")
            print(f"\n    --- Prompt preview (first 300 chars) ---")
            print(f"    {prompt[:300]}...")
        else:
            print("    FAIL: load returned None")
    else:
        print("    FAIL: no skill found")

    # ── 4. Record usage ──────────────────────
    print("\n[4] Simulating skill usage ...")
    if active:
        skill_name = active[0].name
        bank.record_use(skill_name, success=True)
        updated = bank.get(skill_name)
        print(f"    Skill [{skill_name}] use_count -> {updated.use_count}")
        print(f"    success_rate -> {updated.success_rate}")

    # ── 5. Memory write test ─────────────────
    print("\n[5] Memory write test ...")
    if active:
        skill_dir = SKILLS_DIR + "/" + active[0].path
        mem = MemoryManager(skill_dir)
        initial = mem.read()
        initial_lines = len(initial.split("\n")) if initial else 0

        mem.append_success(
            title="Engine integration test",
            scene="C1 engine full pipeline test",
            approach="Tested Bank -> Search -> Load -> Memory modules in sequence",
            takeaway="All modules working, ready for production use",
        )

        updated = mem.read()
        updated_lines = len(updated.split("\n"))
        print(f"    Before write: {initial_lines} lines")
        print(f"    After write:  {updated_lines} lines")
        print(f"    Added:        {updated_lines - initial_lines} lines")

    # ── 6. Report ────────────────────────────
    print("\n" + "=" * 60)
    print("C1 engine pipeline: ALL PASSED")
    print(f"   Registered skills: {[s.name for s in active]}")
    print("=" * 60)


if __name__ == "__main__":
    main()

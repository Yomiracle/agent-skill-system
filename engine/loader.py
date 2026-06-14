"""SkillLoader — 将技能文件加载为可注入 Agent 上下文的文本"""

import json
from pathlib import Path
from typing import Optional

from .models import SkillConfig, SkillBundle, SkillEntry
from .io_utils import safe_child


class SkillLoader:
    """从技能目录加载 SKILL.md + .memory.md + config.json"""

    def __init__(self, bank_dir: str):
        self.bank_dir = Path(bank_dir)

    def load(self, entry: SkillEntry) -> Optional[SkillBundle]:
        """加载一个技能的完整内容"""
        try:
            skill_dir = safe_child(self.bank_dir, entry.path, "skill path")
        except ValueError:
            return None
        if not skill_dir.is_dir():
            return None

        cfg = self._load_config(skill_dir)
        if cfg is None:
            return None

        skill_md = self._read_file(skill_dir / "SKILL.md")
        memory_md = self._read_file(skill_dir / ".memory.md")
        memory_entries = self._parse_memory(memory_md)

        return SkillBundle(
            config=cfg,
            skill_md=skill_md,
            memory_md=memory_md,
            memory_entries=memory_entries,
            path=str(skill_dir.resolve()),
        )

    def build_system_prompt(self, bundle: SkillBundle) -> str:
        """将技能包编译为一段可注入 Agent system prompt 的文本"""
        parts = []

        # 技能标识
        parts.append(f"## 已激活技能：{bundle.config.name} v{bundle.config.version}")
        parts.append(f"> {bundle.config.description}\n")

        # SKILL.md 核心内容
        if bundle.skill_md:
            parts.append("### 技能规范 (SKILL.md)")
            parts.append(bundle.skill_md.strip())

        # .memory.md 经验
        if bundle.memory_entries:
            parts.append("\n### 技能记忆 (.memory.md)")
            parts.append("以下是该技能历史上积累的经验，请优先参考：")
            for mem in bundle.memory_entries[:20]:  # 最多 20 条
                parts.append(mem.to_markdown())

        # 测试提醒
        if bundle.config.input_schema:
            parts.append("\n### 输入要求")
            required = bundle.config.input_schema.get("required", [])
            if required:
                parts.append(f"开始执行前，确保用户提供了：{', '.join(required)}")

        return "\n".join(parts)

    def build_user_prompt(self, task: str, bundle: SkillBundle) -> str:
        """构建注入任务描述的用户提示，包含 input_schema 校验提示"""
        schema = bundle.config.input_schema
        if not schema or not schema.get("required"):
            return task

        required = schema["required"]
        missing_hints = []
        for field in required:
            if field not in task.lower():
                props = schema.get("properties", {})
                desc = props.get(field, {}).get("description", field)
                missing_hints.append(f"- {field}：{desc}")

        if missing_hints:
            return (
                f"{task}\n\n⚠️ 注意：该技能需要以下信息，如您尚未提供，请补充：\n"
                + "\n".join(missing_hints)
            )
        return task

    # ── 内部 ──────────────────────────────

    def _load_config(self, skill_dir: Path) -> Optional[SkillConfig]:
        cfg_path = skill_dir / "config.json"
        if not cfg_path.exists():
            return None
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            return SkillConfig.from_dict(raw)
        except (json.JSONDecodeError, KeyError):
            return None

    @staticmethod
    def _read_file(path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8").strip()

    @staticmethod
    def _parse_memory(memory_md: str) -> list:
        """从 .memory.md 文本中解析 MemoryEntry 列表（轻量实现）"""
        if not memory_md:
            return []

        from .models import MemoryEntry, MemoryType
        import re

        entries = []
        # 按 ### YYYY-MM-DD [类型] 标题 分割
        blocks = re.split(r'\n(?=### \d{4}-\d{2}-\d{2} \[)', memory_md)

        for block in blocks:
            block = block.strip()
            if not block or not block.startswith("### "):
                continue

            # 解析标题行
            header_match = re.match(
                r'### (\d{4}-\d{2}-\d{2}) \[(成功|失败|修正)\]\s*(.*)',
                block
            )
            if not header_match:
                continue

            type_map = {"成功": MemoryType.SUCCESS, "失败": MemoryType.FAILURE, "修正": MemoryType.CORRECTION}
            mem = MemoryEntry(
                date=header_match.group(1),
                type=type_map[header_match.group(2)],
                title=header_match.group(3).strip(),
                scene="",
                detail=block[len(header_match.group(0)):].strip(),
                raw_text=block,
            )
            entries.append(mem)

        return entries

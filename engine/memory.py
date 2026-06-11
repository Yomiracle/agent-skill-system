"""MemoryManager — .memory.md 的自动追加与截断管理"""

from pathlib import Path
from datetime import date
from typing import Optional

from .models import MemoryEntry, MemoryType


class MemoryManager:
    """管理单个技能的 .memory.md 文件"""

    MAX_LINES = 500  # 单文件最大行数，超出的做截断

    def __init__(self, skill_dir: str):
        self.memory_path = Path(skill_dir) / ".memory.md"

    def read(self) -> str:
        """读取当前 .memory.md 全文"""
        if not self.memory_path.exists():
            return ""
        return self.memory_path.read_text(encoding="utf-8").strip()

    def append_success(self, title: str, scene: str, approach: str, takeaway: str):
        """追加一条成功经验"""
        self._append(MemoryEntry(
            date=date.today().isoformat(),
            type=MemoryType.SUCCESS,
            title=title,
            scene=scene,
            detail=f"- 场景：{scene}\n- 做法：{approach}\n- 要点：{takeaway}",
        ))

    def append_failure(self, title: str, scene: str, error: str, root_cause: str, fix: str):
        """追加一条失败经验"""
        self._append(MemoryEntry(
            date=date.today().isoformat(),
            type=MemoryType.FAILURE,
            title=title,
            scene=scene,
            detail=f"- 场景：{scene}\n- 错误：{error}\n- 根因：{root_cause}\n- 修正：{fix}",
        ))

    def append_correction(self, title: str, overwrites: str, reason: str, new_rule: str):
        """追加一条修正记录（覆盖历史中的某条经验）"""
        self._append(MemoryEntry(
            date=date.today().isoformat(),
            type=MemoryType.CORRECTION,
            title=title,
            scene="",
            detail=f"- 覆盖：{overwrites}\n- 原因：{reason}\n- 新规则：{new_rule}",
        ))

    def _append(self, entry: MemoryEntry):
        """将经验记录 prepend 到 .memory.md 顶部"""
        new_block = entry.to_markdown()

        existing = self.read()

        # 确保文件以标题开头
        if not existing:
            skill_name = self.memory_path.parent.name
            existing = f"# 技能记忆：{skill_name}\n\n## 有效经验\n"

        # prepend：新记录插在 "## 有效经验" 之后
        if "## 有效经验" in existing:
            parts = existing.split("## 有效经验", 1)
            updated = (
                parts[0]
                + "## 有效经验\n\n"
                + new_block.strip()
                + "\n\n"
                + parts[1].lstrip("\n")
            )
        else:
            updated = existing + "\n\n" + new_block.strip()

        # 截断保护
        lines = updated.split("\n")
        if len(lines) > self.MAX_LINES:
            # 保留标题 + 最近的经验（前面的）+ 结尾部分
            head = lines[:3]  # 标题区
            body = lines[3:self.MAX_LINES - 3]
            tail = lines[-3:]
            updated = "\n".join(head + [f"// 该文件超过 {self.MAX_LINES} 行，已自动截断"] + body + tail)

        self.memory_path.write_text(updated.strip() + "\n", encoding="utf-8")

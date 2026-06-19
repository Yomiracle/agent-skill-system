"""SkillBank — 技能索引管理：扫描、注册、更新、废弃"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from .models import SkillBankIndex, SkillEntry, SkillStatus, LastEvaluation
from .io_utils import atomic_write_json, safe_child, validate_path_component


class SkillBank:
    """管理 skills/config.json 索引文件 — 技能的注册中心"""

    def __init__(self, bank_path: str):
        """
        Args:
            bank_path: skills/ 目录的绝对路径
        """
        self.bank_dir = Path(bank_path)
        self.index_path = self.bank_dir / "config.json"
        self._index: Optional[SkillBankIndex] = None

    # ── 索引读写 ──────────────────────────────

    def load_index(self) -> SkillBankIndex:
        """从 skills/config.json 加载索引，不存在则创建空索引"""
        if self.index_path.exists():
            try:
                raw = json.loads(self.index_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self._index = SkillBankIndex(version="1.0", skills=[])
            else:
                self._index = SkillBankIndex.from_dict(raw)
        else:
            self._index = SkillBankIndex(version="1.0", skills=[])
        return self._index

    def save_index(self):
        """将内存中的索引写回 skills/config.json"""
        atomic_write_json(self.index_path, self._index.to_dict())

    @property
    def index(self) -> SkillBankIndex:
        if self._index is None:
            self.load_index()
        return self._index

    # ── 技能注册 ──────────────────────────────

    def register(self, name: str, path: str) -> SkillEntry:
        """注册一个新技能或将已有技能重置为 active。

        如果 name 已存在，覆盖旧记录（用于 skill_update 后的重新注册）。
        """
        validate_path_component(path, "skill path")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("skill name must be a non-empty string")
        safe_child(self.bank_dir, path, "skill path")
        now = _now_iso()
        entry = SkillEntry(
            name=name,
            path=path,
            status=SkillStatus.ACTIVE,
            version="1.0.0",
            created_at=now,
            updated_at=now,
            last_used_at=now,
            use_count=0,
            success_rate=1.0,
        )

        # 同名覆盖
        idx = self.index
        existing = [s for s in idx.skills if s.name == name]
        if existing:
            entry.created_at = existing[0].created_at  # 保留原始创建时间
            entry.use_count = existing[0].use_count
            idx.skills = [s for s in idx.skills if s.name != name]

        idx.skills.append(entry)
        self.save_index()
        return entry

    def get(self, name: str) -> Optional[SkillEntry]:
        """按名称查找一个技能"""
        for s in self.index.skills:
            if s.name == name:
                return s
        return None

    def deprecate(self, name: str) -> bool:
        """废弃一个技能（不删除，标记为 deprecated）"""
        entry = self.get(name)
        if not entry:
            return False
        entry.status = SkillStatus.DEPRECATED
        entry.updated_at = _now_iso()
        self.save_index()
        return True

    # ── 使用统计 ──────────────────────────────

    def record_use(self, name: str, success: bool):
        """记录一次技能使用（更新 use_count, last_used_at, success_rate）"""
        entry = self.get(name)
        if not entry:
            return
        entry.use_count += 1
        entry.last_used_at = _now_iso()
        # success_rate 用指数滑动平均，新结果权重 0.3
        delta = 1.0 if success else 0.0
        entry.success_rate = round(entry.success_rate * 0.7 + delta * 0.3, 4)
        self.save_index()

    def update_evaluation(self, name: str, passed: bool, test_count: int, passed_count: int):
        """更新最近一次测试评估结果"""
        entry = self.get(name)
        if not entry:
            return
        entry.last_evaluation = LastEvaluation(
            passed=passed,
            timestamp=_now_iso(),
            test_count=test_count,
            passed_count=passed_count,
        )
        entry.updated_at = _now_iso()
        self.save_index()

    def list_active(self) -> list[SkillEntry]:
        """列出所有 active 状态的技能"""
        return [s for s in self.index.skills if s.status == SkillStatus.ACTIVE]

    def scan_directory(self):
        """扫描 skills/ 目录，自动注册所有有 config.json 但未在索引中的技能目录"""
        idx = self.index
        known_paths = {s.path for s in idx.skills}

        if not self.bank_dir.exists():
            return

        for d in self.bank_dir.iterdir():
            if not d.is_dir():
                continue
            skill_config = d / "config.json"
            if not skill_config.exists():
                continue
            rel_path = d.name
            if rel_path not in known_paths:
                try:
                    raw = json.loads(skill_config.read_text(encoding="utf-8"))
                    self.register(raw.get("name", rel_path), rel_path)
                except (json.JSONDecodeError, OSError, TypeError, ValueError):
                    continue


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

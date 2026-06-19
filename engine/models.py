"""Agent Skill System — 数据结构定义"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class SkillStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DRAFT = "draft"


class MemoryType(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    CORRECTION = "correction"


@dataclass
class LastEvaluation:
    passed: bool
    timestamp: str
    test_count: int
    passed_count: int

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            passed=d["passed"],
            timestamp=d["timestamp"],
            test_count=d["test_count"],
            passed_count=d["passed_count"],
        )


@dataclass
class SkillEntry:
    """Skill Bank 索引中的单条技能记录"""
    name: str
    path: str
    status: SkillStatus
    version: str
    created_at: str
    updated_at: str
    last_used_at: str
    use_count: int
    success_rate: float
    last_evaluation: Optional[LastEvaluation] = None

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            name=d["name"],
            path=d["path"],
            status=SkillStatus(d["status"]),
            version=d["version"],
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            last_used_at=d["last_used_at"],
            use_count=d["use_count"],
            success_rate=d["success_rate"],
            last_evaluation=(
                LastEvaluation.from_dict(d["last_evaluation"])
                if d.get("last_evaluation")
                else None
            ),
        )

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "path": self.path,
            "status": self.status.value,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_used_at": self.last_used_at,
            "use_count": self.use_count,
            "success_rate": self.success_rate,
        }
        if self.last_evaluation:
            d["last_evaluation"] = {
                "passed": self.last_evaluation.passed,
                "timestamp": self.last_evaluation.timestamp,
                "test_count": self.last_evaluation.test_count,
                "passed_count": self.last_evaluation.passed_count,
            }
        return d


@dataclass
class SkillBankIndex:
    """Skill Bank 顶层索引文件 (skills/config.json)"""
    version: str
    skills: list[SkillEntry] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            version=d["version"],
            skills=[SkillEntry.from_dict(s) for s in d.get("skills", [])],
        )

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "skills": [s.to_dict() for s in self.skills],
        }


@dataclass
class SkillConfig:
    """单个技能的 config.json"""
    name: str
    version: str
    description: str
    trigger_keywords: list[str]
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    max_context_percent: int = 30
    created_at: str = ""

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            name=d["name"],
            version=d["version"],
            description=d["description"],
            trigger_keywords=d.get("trigger_keywords", []),
            input_schema=d.get("input_schema", {}),
            output_schema=d.get("output_schema", {}),
            tags=d.get("tags", []),
            dependencies=d.get("dependencies", []),
            max_context_percent=d.get("max_context_percent", 30),
            created_at=d.get("created_at", ""),
        )


@dataclass
class MemoryEntry:
    """.memory.md 中的单条经验记录"""
    date: str
    type: MemoryType
    title: str
    scene: str
    detail: str   # 成功=做法+要点，失败=错误+根因+修正，修正=覆盖+原因+新规则
    raw_text: str = ""  # 原始 markdown 片段

    def to_markdown(self) -> str:
        type_label = {
            MemoryType.SUCCESS: "成功",
            MemoryType.FAILURE: "失败",
            MemoryType.CORRECTION: "修正",
        }
        return self.raw_text or f"### {self.date} [{type_label[self.type]}] {self.title}\n- 场景：{self.scene}\n{self.detail}\n"


@dataclass
class SkillBundle:
    """一次技能加载的完整内容包"""
    config: SkillConfig
    skill_md: str           # SKILL.md 全文
    memory_md: str          # .memory.md 全文（或截断版）
    memory_entries: list[MemoryEntry]
    path: str               # 技能目录绝对路径

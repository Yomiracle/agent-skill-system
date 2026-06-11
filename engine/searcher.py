"""SkillSearcher — 任务到技能的匹配检索"""

import json
import re
from pathlib import Path
from typing import Optional

from .models import SkillConfig, SkillEntry, SkillBankIndex


class SkillSearcher:
    """根据用户任务描述检索匹配的技能"""

    def __init__(self, bank_dir: str):
        self.bank_dir = Path(bank_dir)

    def search(self, task_description: str, bank_index: SkillBankIndex,
               top_n: int = 3) -> list[tuple[SkillEntry, SkillConfig, float]]:
        """
        从 Skill Bank 中检索匹配的技能。
        返回: [(skill_entry, skill_config, score), ...]，按 score 降序
        """
        active = [s for s in bank_index.skills if s.status.value == "active"]
        if not active:
            return []

        task_lower = task_description.lower()
        results: list[tuple[SkillEntry, SkillConfig, float]] = []

        for entry in active:
            cfg = self._load_config(entry)
            if cfg is None:
                continue

            score = self._score(task_lower, entry, cfg)
            if score > 0:
                results.append((entry, cfg, score))

        # 按分数降序
        results.sort(key=lambda x: x[2], reverse=True)

        # 去重 + 截断 + 最低分数过滤
        MIN_SCORE = 15  # 低于此分的忽略（噪声过滤）
        seen = set()
        deduped = []
        for entry, cfg, score in results:
            if score < MIN_SCORE:
                continue
            if entry.name not in seen:
                seen.add(entry.name)
                deduped.append((entry, cfg, score))
            if len(deduped) >= top_n:
                break

        return deduped

    def _load_config(self, entry: SkillEntry) -> Optional[SkillConfig]:
        cfg_path = self.bank_dir / entry.path / "config.json"
        if not cfg_path.exists():
            return None
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            return SkillConfig.from_dict(raw)
        except (json.JSONDecodeError, KeyError):
            return None

    def _score(self, task_lower: str, entry: SkillEntry, cfg: SkillConfig) -> float:
        """对技能与任务的匹配度打分"""
        score = 0.0

        # 1. 关键词命中（多粒度匹配）
        keyword_hits = 0
        for kw in cfg.trigger_keywords:
            kw_lower = kw.lower()
            # 完整匹配
            if kw_lower in task_lower:
                keyword_hits += 1
                continue
            # 短关键词（≤3字）做逐字散匹配，"审合同" 能命中 "审一下这份合同"
            if len(kw) <= 3:
                chars = list(kw_lower)
                # 2字词：两字都在任务中，且间距不超过5字
                if len(chars) == 2:
                    p0 = task_lower.find(chars[0])
                    p1 = task_lower.find(chars[1])
                    if p0 >= 0 and p1 >= 0 and abs(p1 - p0) <= 10:
                        keyword_hits += 0.5
                        continue
                # 3字词：每字都在，且总跨度不超过15字
                elif len(chars) == 3:
                    positions = [task_lower.find(c) for c in chars]
                    if all(p >= 0 for p in positions):
                        span = max(positions) - min(positions)
                        if span <= 20:
                            keyword_hits += 0.5
                            continue
                # 单字词：直接匹配
                elif len(chars) == 1:
                    if chars[0] in task_lower:
                        keyword_hits += 0.3
                        continue
            # 长关键词（≥4字）做三字滑窗 + 二字前缀/尾缀匹配
            if len(kw) >= 4:
                hit_count = 0
                # 三字滑窗
                for i in range(len(kw_lower) - 2):
                    if kw_lower[i:i+3] in task_lower:
                        hit_count += 1
                # 二字前缀（如 "论文审查" → "论文"）
                prefix_2 = kw_lower[:2]
                if prefix_2 in task_lower:
                    hit_count += 1
                # 二字尾缀
                suffix_2 = kw_lower[-2:]
                if suffix_2 in task_lower:
                    hit_count += 1
                if hit_count >= 1:
                    keyword_hits += 0.3 * hit_count

        if keyword_hits > 0:
            score += min(keyword_hits * 30, 90)

        # 2. 描述语义重叠（交集词数）
        desc_words = set(cfg.description.lower().split())
        task_words = set(task_lower.split())
        desc_overlap = len(desc_words & task_words)
        if desc_overlap > 0:
            score += min(desc_overlap * 5, 30)

        # 如果前两步都没有得分，直接返回 0（不做后面的统计加权）
        if score == 0:
            return 0.0

        # 3. 使用频率奖励（只在有内容匹配时生效）
        if entry.use_count > 0:
            score += min(entry.use_count * 0.5, 10)

        # 4. 成功率惩罚
        if entry.success_rate < 0.5:
            score *= 0.5

        # 5. 最近评估失败惩罚
        if entry.last_evaluation and not entry.last_evaluation.passed:
            score *= 0.5

        return round(score, 2)

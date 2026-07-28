"""Deduplicate weekly raw items."""

from __future__ import annotations

from pydantic import BaseModel, Field

from gitpulse.models.weekly import WeeklyRawItem


class DeduplicationGroup(BaseModel):
    item_ids: list[str]
    reason: str


class DeduplicationResult(BaseModel):
    items: list[WeeklyRawItem]
    merged_groups: list[DeduplicationGroup] = Field(default_factory=list)
    ambiguous_groups: list[DeduplicationGroup] = Field(default_factory=list)


class WeeklyDeduplicator:
    """Merge exactly repeated report items while preserving sources."""

    def deduplicate(self, items: list[WeeklyRawItem]) -> DeduplicationResult:
        by_key: dict[tuple[str | None, str, str], WeeklyRawItem] = {}
        groups: list[DeduplicationGroup] = []
        for item in items:
            key = (item.repository_id, item.category_hint or "", item.title.lower())
            existing = by_key.get(key)
            if not existing:
                by_key[key] = item
                continue
            existing.sources.extend(source for source in item.sources if source not in existing.sources)
            if item.result and item.result not in (existing.result or ""):
                existing.result = "；".join(part for part in [existing.result, item.result] if part)
            groups.append(
                DeduplicationGroup(item_ids=[existing.id, item.id], reason="相同标题和分类自动合并")
            )
        return DeduplicationResult(items=list(by_key.values()), merged_groups=groups)

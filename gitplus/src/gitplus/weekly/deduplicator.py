"""Deduplicate weekly raw items."""

from __future__ import annotations

from pydantic import BaseModel, Field

from gitplus.models.weekly import WeeklyRawItem


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
            commit_hash = next(
                (
                    source.commit_hash
                    for source in item.sources
                    if source.commit_hash
                ),
                None,
            )
            identity = (
                f"commit:{commit_hash}"
                if commit_hash
                else item.title.casefold()
            )
            key = (item.repository_id, item.category_hint or "", identity)
            existing = by_key.get(key)
            if not existing:
                by_key[key] = item
                continue
            existing.sources.extend(source for source in item.sources if source not in existing.sources)
            if item.result and item.result not in (existing.result or ""):
                existing.result = "；".join(part for part in [existing.result, item.result] if part)
            groups.append(
                DeduplicationGroup(
                    item_ids=[existing.id, item.id],
                    reason=(
                        "关联到相同 Commit，已合并来源"
                        if commit_hash
                        else "相同仓库、标题和分类自动合并"
                    ),
                )
            )
        return DeduplicationResult(items=list(by_key.values()), merged_groups=groups)

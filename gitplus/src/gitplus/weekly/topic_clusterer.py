"""Deterministic weekly topic clustering."""

from __future__ import annotations

from gitplus.models.weekly import WeeklyRawItem, WeeklyTopicCandidate


class WeeklyTopicClusterer:
    """Cluster completed items by repository, scope, and category."""

    def cluster(self, items: list[WeeklyRawItem]) -> list[WeeklyTopicCandidate]:
        groups: dict[tuple[str | None, str | None, str], list[WeeklyRawItem]] = {}
        for item in items:
            category = item.category_hint or "completed"
            if category != "completed":
                continue
            key = (item.repository_id, item.scope or self._directory_scope(item), category)
            groups.setdefault(key, []).append(item)
        candidates: list[WeeklyTopicCandidate] = []
        for index, ((_, scope, _), group_items) in enumerate(groups.items(), start=1):
            title = scope or group_items[0].title
            candidates.append(
                WeeklyTopicCandidate(
                    id=f"topic_{index}",
                    title_hint=title,
                    items=group_items,
                    repository_names=sorted({item.repository_name for item in group_items if item.repository_name}),
                    scopes=sorted({scope} if scope else set()),
                    confidence="medium" if len(group_items) > 1 else "high",
                    reason="按 scope 或目录进行确定性聚合",
                )
            )
        return candidates

    def _directory_scope(self, item: WeeklyRawItem) -> str | None:
        if not item.files:
            return None
        first = item.files[0]
        return first.split("/", 1)[0] if "/" in first else None


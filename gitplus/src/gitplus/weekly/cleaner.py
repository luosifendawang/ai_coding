"""Weekly input cleanup before rule-based or AI generation."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from gitplus.models.weekly import WeeklyGenerationInput, WeeklyRawItem
from gitplus.weekly.deduplicator import (
    DeduplicationGroup,
    WeeklyDeduplicator,
)
from gitplus.weekly.normalizer import WeeklyNormalizer

PLACEHOLDER_PATTERNS = [
    re.compile(r"^module:\s*brief and clear title$", re.IGNORECASE),
    re.compile(r"^more detailed issue description$", re.IGNORECASE),
    re.compile(r"^test result:\s*$", re.IGNORECASE),
]
LOW_INFORMATION_TEXT = {"init", "test", "测试", "初始化"}


class WeeklyCleanupResult(BaseModel):
    items: list[WeeklyRawItem] = Field(default_factory=list)
    merged_groups: list[DeduplicationGroup] = Field(default_factory=list)
    template_items: list[WeeklyRawItem] = Field(default_factory=list)
    low_information_items: list[WeeklyRawItem] = Field(default_factory=list)


class WeeklyDataCleaner:
    """Remove placeholders and exact duplicates without merging across repos."""

    def __init__(
        self,
        normalizer: WeeklyNormalizer | None = None,
        deduplicator: WeeklyDeduplicator | None = None,
    ) -> None:
        self.normalizer = normalizer or WeeklyNormalizer()
        self.deduplicator = deduplicator or WeeklyDeduplicator()

    def clean(self, generation_input: WeeklyGenerationInput) -> WeeklyCleanupResult:
        accepted: list[WeeklyRawItem] = []
        templates: list[WeeklyRawItem] = []
        low_information: list[WeeklyRawItem] = []
        for item in self.normalizer.normalize(generation_input):
            self._remove_repeated_description(item)
            if self._is_template(item):
                templates.append(item)
            elif self._is_low_information(item):
                low_information.append(item)
            else:
                accepted.append(item)
        deduplicated = self.deduplicator.deduplicate(accepted)
        return WeeklyCleanupResult(
            items=deduplicated.items,
            merged_groups=deduplicated.merged_groups,
            template_items=templates,
            low_information_items=low_information,
        )

    def accepted_source_labels(
        self, generation_input: WeeklyGenerationInput
    ) -> set[str]:
        return {
            source.label
            for item in self.clean(generation_input).items
            for source in item.sources
        }

    def _remove_repeated_description(self, item: WeeklyRawItem) -> None:
        if not item.description:
            return
        title = self._normalize(item.title)
        description = self._normalize(item.description)
        if description == title:
            item.description = None

    def _is_template(self, item: WeeklyRawItem) -> bool:
        values = [item.title, item.description or "", item.result or ""]
        return any(
            pattern.fullmatch(value.strip())
            for pattern in PLACEHOLDER_PATTERNS
            for value in values
            if value.strip()
        )

    def _is_low_information(self, item: WeeklyRawItem) -> bool:
        title = self._normalize(item.title)
        has_detail = bool(
            (item.description and len(self._normalize(item.description)) > 3)
            or (item.result and len(self._normalize(item.result)) > 3)
        )
        return not has_detail and (
            title in LOW_INFORMATION_TEXT or len(title) < 4
        )

    def _normalize(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip().casefold()

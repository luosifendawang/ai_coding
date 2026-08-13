"""Rule-based weekly report generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, cast
from uuid import uuid4

from gitplus.config import WeeklyConfig
from gitplus.models.source import WeeklySourceReference
from gitplus.models.weekly import (
    WeeklyGenerationInput,
    WeeklyRawItem,
    WeeklyReportDraft,
    WeeklyReportItem,
    WeeklyReportTopic,
    WeeklyUserNote,
)
from gitplus.weekly.cleaner import WeeklyDataCleaner
from gitplus.weekly.confidence import WeeklyConfidenceCalculator
from gitplus.weekly.fact_validator import WeeklyFactValidator
from gitplus.weekly.normalizer import WeeklyNormalizer
from gitplus.weekly.topic_clusterer import WeeklyTopicClusterer


class RuleBasedWeeklyGenerator:
    """Build a deterministic weekly draft without calling an LLM."""

    def __init__(
        self,
        *,
        config: WeeklyConfig | None = None,
        normalizer: WeeklyNormalizer | None = None,
        cleaner: WeeklyDataCleaner | None = None,
        clusterer: WeeklyTopicClusterer | None = None,
        confidence: WeeklyConfidenceCalculator | None = None,
        validator: WeeklyFactValidator | None = None,
    ) -> None:
        self.config = config or WeeklyConfig()
        self.normalizer = normalizer or WeeklyNormalizer()
        self.cleaner = cleaner or WeeklyDataCleaner(normalizer=self.normalizer)
        self.clusterer = clusterer or WeeklyTopicClusterer()
        self.confidence = confidence or WeeklyConfidenceCalculator()
        self.validator = validator or WeeklyFactValidator()

    def generate(self, generation_input: WeeklyGenerationInput) -> WeeklyReportDraft:
        current = datetime.now(timezone.utc)
        deduped = self.cleaner.clean(generation_input).items
        topics = self.clusterer.cluster(deduped)[: self.config.max_topics]
        draft = WeeklyReportDraft(
            id=f"weekly_{uuid4().hex[:12]}",
            title=f"{generation_input.date_range.label}开发周报",
            date_range=generation_input.date_range,
            completed=[self._topic(topic) for topic in topics],
            debugging=self._section_items(deduped, "debugging"),
            testing=self._section_items(deduped, "testing"),
            risks=[self._note_item(note, "risk") for note in generation_input.risks],
            next_week=[self._note_item(note, "plan") for note in generation_input.next_week_plans],
            generator="rule_based",
            created_at=current,
            updated_at=current,
        )
        draft.needs_confirmation = self._needs_confirmation(draft)
        validation = self.validator.validate(draft, generation_input)
        draft.source_coverage = validation.source_coverage
        return draft

    def _topic(self, candidate) -> WeeklyReportTopic:  # type: ignore[no-untyped-def]
        items = [self._raw_item(item) for item in candidate.items[: self.config.max_items_per_topic]]
        return WeeklyReportTopic(
            id=candidate.id,
            title=self._sentence(candidate.title_hint or "工作事项"),
            summary=self._topic_summary(candidate.items),
            category="completed",
            items=items,
            sources=self._unique_sources([source for item in candidate.items for source in item.sources]),
            confidence=candidate.confidence,
            confirmed_by_user=candidate.confidence == "high",
        )

    def _section_items(self, items: list[WeeklyRawItem], category: str) -> list[WeeklyReportItem]:
        section_items = [self._raw_item(item) for item in items if item.category_hint == category]
        return section_items[: self.config.max_items_per_topic]

    def _raw_item(self, item: WeeklyRawItem) -> WeeklyReportItem:
        confidence = cast(
            Literal["high", "medium", "low"],
            self.confidence.for_raw_item(item),
        )
        content = item.result or item.description or item.title
        if content == item.title:
            content = self._sentence(content)
        else:
            content = f"{self._sentence(item.title)}：{self._sentence(content)}"
        report_item = WeeklyReportItem(
            id=f"item_{item.id}",
            content=content,
            title=item.title,
            description=item.description,
            result=item.result,
            confidence=confidence,
            sources=self._unique_sources(item.sources),
            confirmed_by_user=confidence == "high",
        )
        report_item.needs_confirmation = self.confidence.requires_confirmation(
            report_item,
            require_medium=self.config.require_medium_confirmation,
        )
        return report_item

    def _note_item(self, note: WeeklyUserNote, prefix: str) -> WeeklyReportItem:
        source = WeeklySourceReference(source_type="user_note", source_id=note.id, title=note.content)
        confidence = cast(
            Literal["high", "medium", "low"],
            "high" if note.confirmed_by_user else "medium",
        )
        item = WeeklyReportItem(
            id=f"{prefix}_{note.id}",
            content=self._sentence(note.content),
            title=note.content,
            confidence=confidence,
            sources=[source],
            confirmed_by_user=note.confirmed_by_user,
        )
        item.needs_confirmation = self.confidence.requires_confirmation(
            item,
            require_medium=self.config.require_medium_confirmation,
        )
        return item

    def _needs_confirmation(self, draft: WeeklyReportDraft) -> list[WeeklyReportItem]:
        items: list[WeeklyReportItem] = []
        for topic in draft.completed:
            items.extend(item for item in topic.items if item.needs_confirmation)
        for section in [draft.debugging, draft.testing, draft.risks, draft.next_week]:
            items.extend(item for item in section if item.needs_confirmation)
        return items

    def _topic_summary(self, items: list[WeeklyRawItem]) -> str:
        count = len(items)
        if count == 1:
            return self._sentence(items[0].title)
        title = self._sentence(items[0].scope or items[0].title)
        return f"围绕 {title} 合并整理了 {count} 条有来源的工作记录。"

    def _sentence(self, value: str) -> str:
        return " ".join(value.split()).strip("。")

    def _unique_sources(self, sources: list[WeeklySourceReference]) -> list[WeeklySourceReference]:
        unique: dict[str, WeeklySourceReference] = {}
        for source in sources:
            unique.setdefault(source.label, source)
        return list(unique.values())

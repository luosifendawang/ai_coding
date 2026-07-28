"""Weekly confidence calculation."""

from __future__ import annotations

from gitpulse.models.weekly import WeeklyRawItem, WeeklyReportItem


class WeeklyConfidenceCalculator:
    """Assign confidence from evidence type and aggregation level."""

    def for_raw_item(self, item: WeeklyRawItem) -> str:
        if item.source_type in {"commit", "record", "worklog"} and item.sources:
            return "high"
        if item.source_type == "uncommitted" and item.sources:
            return "medium"
        return "medium" if item.sources else "low"

    def requires_confirmation(self, item: WeeklyReportItem, *, require_medium: bool = True) -> bool:
        if item.confidence == "low":
            return True
        return require_medium and item.confidence == "medium" and not item.confirmed_by_user

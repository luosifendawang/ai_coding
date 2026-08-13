"""Weekly source validation."""

from __future__ import annotations

from pydantic import BaseModel

from gitplus.models.source import WeeklySourceReference
from gitplus.models.weekly import WeeklyGenerationInput


class SourceValidationIssue(BaseModel):
    source: str
    reason: str


class SourceResolver:
    """Validate report source references against current generation input."""

    def __init__(self, generation_input: WeeklyGenerationInput) -> None:
        self.valid_labels = self._valid_labels(generation_input)

    def validate_sources(self, references: list[WeeklySourceReference]) -> list[SourceValidationIssue]:
        issues: list[SourceValidationIssue] = []
        for reference in references:
            if reference.label not in self.valid_labels:
                issues.append(
                    SourceValidationIssue(source=reference.label, reason="来源不存在于本次周报输入")
                )
        return issues

    def _valid_labels(self, generation_input: WeeklyGenerationInput) -> set[str]:
        labels: set[str] = set()
        for commit in generation_input.commits:
            labels.add(f"commit:{commit.commit_hash[:8]}")
        for record in generation_input.commit_records:
            labels.add(f"record:{record.id}")
        for worklog in generation_input.worklogs:
            labels.add(f"worklog:{worklog.id}")
        for change in generation_input.uncommitted_changes:
            labels.add(f"uncommitted:{change.repository_id}:{change.summary}")
        for note in [*generation_input.risks, *generation_input.next_week_plans, *generation_input.user_notes]:
            labels.add(f"user_note:{note.id}")
        return labels

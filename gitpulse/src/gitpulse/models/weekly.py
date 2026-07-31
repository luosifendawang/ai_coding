"""Weekly report input and output models."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from gitpulse.models.source import WeeklySourceReference
from gitpulse.models.storage import CommitRecord

ConfidenceLevel = Literal["high", "medium", "low"]


class WeeklyDateRange(BaseModel):
    date_from: date
    date_to: date
    datetime_from: datetime
    datetime_to: datetime
    timezone: str
    label: str

    @model_validator(mode="after")
    def validate_range(self) -> WeeklyDateRange:
        if self.datetime_to < self.datetime_from:
            raise ValueError("weekly date range end must not be earlier than start")
        return self


class WeeklyCommitInput(BaseModel):
    commit_hash: str
    short_hash: str
    repository_id: str
    repository_name: str
    branch: str | None = None
    author_email: str
    committed_at: datetime
    subject: str
    body: str = ""
    files: list[str] = Field(default_factory=list)
    insertions: int = 0
    deletions: int = 0
    source_record_ids: list[str] = Field(default_factory=list)


class WeeklyWorklogInput(BaseModel):
    id: str
    repository_id: str | None = None
    repository_name: str | None = None
    work_date: date
    work_type: str
    title: str
    description: str | None = None
    result: str | None = None
    duration_minutes: int | None = None
    tags: list[str] = Field(default_factory=list)


class WeeklyUncommittedInput(BaseModel):
    repository_id: str
    repository_name: str
    branch: str | None = None
    summary: str
    files: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel
    confirmed_by_user: bool = False


class WeeklyUserNote(BaseModel):
    id: str
    note_type: str
    content: str
    confirmed_by_user: bool = True


class WeeklyGenerationInput(BaseModel):
    date_range: WeeklyDateRange
    commits: list[WeeklyCommitInput] = Field(default_factory=list)
    commit_records: list[CommitRecord] = Field(default_factory=list)
    worklogs: list[WeeklyWorklogInput] = Field(default_factory=list)
    uncommitted_changes: list[WeeklyUncommittedInput] = Field(default_factory=list)
    user_notes: list[WeeklyUserNote] = Field(default_factory=list)
    risks: list[WeeklyUserNote] = Field(default_factory=list)
    next_week_plans: list[WeeklyUserNote] = Field(default_factory=list)


class WeeklyRawItem(BaseModel):
    id: str
    source_type: str
    category_hint: str | None = None
    repository_id: str | None = None
    repository_name: str | None = None
    scope: str | None = None
    commit_type: str | None = None
    title: str
    description: str | None = None
    result: str | None = None
    files: list[str] = Field(default_factory=list)
    occurred_at: datetime | None = None
    sources: list[WeeklySourceReference] = Field(default_factory=list)


class WeeklyTopicCandidate(BaseModel):
    id: str
    title_hint: str | None = None
    items: list[WeeklyRawItem]
    repository_names: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel
    reason: str


class WeeklyReportItem(BaseModel):
    id: str
    content: str
    title: str | None = None
    description: str | None = None
    result: str | None = None
    confidence: ConfidenceLevel
    sources: list[WeeklySourceReference] = Field(default_factory=list)
    confirmed_by_user: bool = False
    needs_confirmation: bool = False
    notes: list[str] = Field(default_factory=list)


class WeeklyReportTopic(BaseModel):
    id: str
    title: str
    summary: str | None = None
    category: str
    items: list[WeeklyReportItem] = Field(default_factory=list)
    sources: list[WeeklySourceReference] = Field(default_factory=list)
    confidence: ConfidenceLevel
    confirmed_by_user: bool = False


class WeeklyReportDraft(BaseModel):
    id: str
    title: str
    date_range: WeeklyDateRange
    completed: list[WeeklyReportTopic] = Field(default_factory=list)
    debugging: list[WeeklyReportItem] = Field(default_factory=list)
    testing: list[WeeklyReportItem] = Field(default_factory=list)
    risks: list[WeeklyReportItem] = Field(default_factory=list)
    next_week: list[WeeklyReportItem] = Field(default_factory=list)
    needs_confirmation: list[WeeklyReportItem] = Field(default_factory=list)
    source_coverage: float = Field(default=0.0, ge=0, le=1)
    generator: str
    created_at: datetime
    updated_at: datetime


class WeeklyReport(BaseModel):
    id: str
    title: str
    date_range: WeeklyDateRange
    completed: list[WeeklyReportTopic] = Field(default_factory=list)
    debugging: list[WeeklyReportItem] = Field(default_factory=list)
    testing: list[WeeklyReportItem] = Field(default_factory=list)
    risks: list[WeeklyReportItem] = Field(default_factory=list)
    next_week: list[WeeklyReportItem] = Field(default_factory=list)
    source_coverage: float = Field(ge=0, le=1)
    status: str
    content_markdown: str
    generator: str
    version: int = 1
    parent_report_id: str | None = None
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None = None


class WeeklyValidationIssue(BaseModel):
    level: str
    issue_type: str
    section: str
    item_id: str | None = None
    content: str | None = None
    reason: str
    suggestion: str | None = None


class WeeklyValidationResult(BaseModel):
    status: Literal["pass", "warning", "fail"]
    source_coverage: float
    issues: list[WeeklyValidationIssue] = Field(default_factory=list)
    blocked_item_ids: list[str] = Field(default_factory=list)
    requires_confirmation_ids: list[str] = Field(default_factory=list)

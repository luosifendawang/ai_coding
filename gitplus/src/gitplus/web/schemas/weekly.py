"""Weekly report Web API schemas."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

AuthorValue = Annotated[str, StringConstraints(strip_whitespace=True, max_length=320)]
SourceIdValue = Annotated[str, StringConstraints(max_length=500)]


class WeeklyRangeRequest(BaseModel):
    range_kind: Literal["current", "last", "custom"] = "current"
    date_from: date | None = None
    date_to: date | None = None
    authors: list[AuthorValue] = Field(default_factory=list, max_length=20)
    include_uncommitted: bool = False

    @model_validator(mode="after")
    def validate_range(self) -> WeeklyRangeRequest:
        if self.range_kind == "custom":
            if self.date_from is None or self.date_to is None:
                raise ValueError("自定义周期需要开始日期和结束日期")
            if self.date_from > self.date_to:
                raise ValueError("开始日期不能晚于结束日期")
        return self


class WeeklyGenerateWebRequest(WeeklyRangeRequest):
    use_ai: bool = False
    excluded_source_ids: list[SourceIdValue] = Field(
        default_factory=list, max_length=500
    )
    user_context: str = Field(default="", max_length=4000)


class WeeklySourceEdit(BaseModel):
    source_type: str = Field(max_length=30)
    source_id: str = Field(max_length=500)
    repository_id: str | None = Field(default=None, max_length=100)
    commit_hash: str | None = Field(default=None, max_length=64)
    title: str | None = Field(default=None, max_length=500)
    repository_name: str | None = Field(default=None, max_length=200)
    confidence: Literal["high", "medium", "low"] = "high"
    files: list[str] = Field(default_factory=list, max_length=100)


class WeeklyItemEdit(BaseModel):
    id: str = Field(max_length=120)
    content: str = Field(min_length=1, max_length=10000)
    title: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    result: str | None = Field(default=None, max_length=5000)
    confidence: Literal["high", "medium", "low"] = "high"
    sources: list[WeeklySourceEdit] = Field(
        default_factory=list, max_length=50
    )
    confirmed_by_user: bool = False
    notes: list[str] = Field(default_factory=list, max_length=20)


class WeeklyTopicEdit(BaseModel):
    id: str = Field(max_length=120)
    title: str = Field(min_length=1, max_length=300)
    summary: str | None = Field(default=None, max_length=5000)
    category: str = Field(default="completed", max_length=50)
    items: list[WeeklyItemEdit] = Field(default_factory=list, max_length=100)
    confidence: Literal["high", "medium", "low"] = "high"
    confirmed_by_user: bool = False


class WeeklyReportEdit(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    completed: list[WeeklyTopicEdit] = Field(
        default_factory=list, max_length=50
    )
    debugging: list[WeeklyItemEdit] = Field(
        default_factory=list, max_length=100
    )
    testing: list[WeeklyItemEdit] = Field(
        default_factory=list, max_length=100
    )
    risks: list[WeeklyItemEdit] = Field(
        default_factory=list, max_length=100
    )
    next_week: list[WeeklyItemEdit] = Field(
        default_factory=list, max_length=100
    )


class WeeklyUpdateRequest(BaseModel):
    version: int = Field(ge=1)
    report: WeeklyReportEdit


class WeeklyVersionRequest(BaseModel):
    version: int = Field(ge=1)

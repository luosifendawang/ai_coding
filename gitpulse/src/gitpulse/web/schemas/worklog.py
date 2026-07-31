"""Worklog API request schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from gitpulse.models.worklog import WorklogSource, WorklogType


class WorklogWriteRequest(BaseModel):
    occurred_at: datetime
    type: WorklogType
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    result: str | None = Field(default=None, max_length=10000)
    duration_minutes: int | None = Field(default=None, ge=1, le=10080)
    tags: list[str] = Field(default_factory=list, max_length=20)
    related_commit_hash: str | None = Field(default=None, max_length=64)
    source: WorklogSource = "manual"


class WorklogUpdateRequest(BaseModel):
    occurred_at: datetime | None = None
    type: WorklogType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    result: str | None = Field(default=None, max_length=10000)
    duration_minutes: int | None = Field(default=None, ge=1, le=10080)
    tags: list[str] | None = Field(default=None, max_length=20)
    related_commit_hash: str | None = Field(default=None, max_length=64)


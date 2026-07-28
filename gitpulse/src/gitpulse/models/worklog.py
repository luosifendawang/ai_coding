"""Worklog domain models."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

WorklogType = Literal[
    "debug",
    "research",
    "meeting",
    "support",
    "setup",
    "test",
    "learning",
    "document",
    "other",
]


class Worklog(BaseModel):
    id: str
    repository_id: str | None = None
    work_date: date
    work_type: WorklogType
    title: str
    description: str | None = None
    result: str | None = None
    duration_minutes: int | None = None
    tags: list[str] = Field(default_factory=list)
    confirmed_by_user: bool = True
    created_at: datetime
    updated_at: datetime


class WorklogCreate(BaseModel):
    repository_id: str | None = None
    work_date: date
    work_type: WorklogType
    title: str
    description: str | None = None
    result: str | None = None
    duration_minutes: int | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("worklog title must not be empty")
        return value.strip()

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("duration_minutes must be positive")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        normalized = []
        for tag in value:
            cleaned = tag.strip()
            if cleaned and cleaned not in normalized:
                if len(cleaned) > 50:
                    raise ValueError("tag must not exceed 50 characters")
                normalized.append(cleaned)
        if len(normalized) > 20:
            raise ValueError("tags must not exceed 20 items")
        return normalized


class WorklogUpdate(BaseModel):
    work_date: date | None = None
    work_type: WorklogType | None = None
    title: str | None = None
    description: str | None = None
    result: str | None = None
    duration_minutes: int | None = None
    tags: list[str] | None = None
    confirmed_by_user: bool | None = None

    @field_validator("title")
    @classmethod
    def validate_optional_title(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("worklog title must not be empty")
        return value.strip() if value is not None else None


class WorklogFilters(BaseModel):
    repository_id: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    work_types: list[str] | None = None
    tags: list[str] | None = None
    confirmed_only: bool = True
    limit: int = 100
    offset: int = 0


"""Worklog domain models."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

WorklogType = Literal[
    "development",
    "debug",
    "review",
    "research",
    "meeting",
    "support",
    "setup",
    "test",
    "learning",
    "document",
    "other",
]
WorklogSource = Literal["manual", "copy", "import"]


class Worklog(BaseModel):
    id: str
    repository_id: str | None = None
    work_date: date
    occurred_at: datetime | None = None
    work_type: WorklogType
    title: str
    description: str | None = None
    result: str | None = None
    duration_minutes: int | None = None
    tags: list[str] = Field(default_factory=list)
    related_commit_hash: str | None = None
    source: WorklogSource = "manual"
    confirmed_by_user: bool = True
    created_at: datetime
    updated_at: datetime


class WorklogCreate(BaseModel):
    repository_id: str | None = None
    work_date: date
    occurred_at: datetime | None = None
    work_type: WorklogType
    title: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    result: str | None = Field(default=None, max_length=10000)
    duration_minutes: int | None = None
    tags: list[str] = Field(default_factory=list)
    related_commit_hash: str | None = Field(default=None, max_length=64)
    source: WorklogSource = "manual"

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("worklog title must not be empty")
        return value.strip()

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, value: int | None) -> int | None:
        if value is not None and not 1 <= value <= 10080:
            raise ValueError("duration_minutes must be between 1 and 10080")
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

    @field_validator("related_commit_hash")
    @classmethod
    def validate_commit_hash(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        cleaned = value.strip().lower()
        if not 7 <= len(cleaned) <= 64 or any(
            character not in "0123456789abcdef" for character in cleaned
        ):
            raise ValueError("related_commit_hash must be a hexadecimal Git hash")
        return cleaned


class WorklogUpdate(BaseModel):
    work_date: date | None = None
    occurred_at: datetime | None = None
    work_type: WorklogType | None = None
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    result: str | None = Field(default=None, max_length=10000)
    duration_minutes: int | None = None
    tags: list[str] | None = None
    related_commit_hash: str | None = Field(default=None, max_length=64)
    confirmed_by_user: bool | None = None

    @field_validator("title")
    @classmethod
    def validate_optional_title(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("worklog title must not be empty")
        return value.strip() if value is not None else None

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, value: int | None) -> int | None:
        return WorklogCreate.validate_duration(value)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        return WorklogCreate.normalize_tags(value) if value is not None else None

    @field_validator("related_commit_hash")
    @classmethod
    def validate_commit_hash(cls, value: str | None) -> str | None:
        return WorklogCreate.validate_commit_hash(value)


class WorklogFilters(BaseModel):
    repository_id: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    work_types: list[str] | None = None
    tags: list[str] | None = None
    keyword: str | None = Field(default=None, max_length=200)
    confirmed_only: bool = True
    limit: int = Field(default=100, ge=1)
    offset: int = Field(default=0, ge=0)

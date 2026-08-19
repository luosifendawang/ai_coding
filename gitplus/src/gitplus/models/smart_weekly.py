"""Models for the independent smart weekly assistant."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class SmartWeeklySource(BaseModel):
    id: str
    kind: str
    occurred_at: str
    title: str
    summary: str = ""
    repository: str
    source_ref: str | None = None


class SmartWeeklySection(BaseModel):
    key: Literal["completed", "quality", "risks", "next_week"]
    title: str
    items: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class SmartWeeklyDraft(BaseModel):
    title: str
    date_from: date
    date_to: date
    overview: str = ""
    sections: list[SmartWeeklySection]
    source_ids: list[str]
    markdown: str
    generator: str
    warnings: list[str] = Field(default_factory=list)


class SmartWeeklyGenerateRequest(BaseModel):
    date_from: date
    date_to: date
    source_ids: list[str] = Field(default_factory=list)
    use_ai: bool = True
    extra_context: str = Field(default="", max_length=4000)


class SmartWeeklyRefineRequest(BaseModel):
    draft: SmartWeeklyDraft
    instruction: str = Field(min_length=1, max_length=2000)


class SmartWeeklySaveRequest(BaseModel):
    draft: SmartWeeklyDraft


class SmartWeeklyUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    markdown: str = Field(min_length=1, max_length=100000)
    expected_version: int = Field(ge=1)

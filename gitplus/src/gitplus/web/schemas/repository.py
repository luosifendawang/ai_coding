"""Repository workbench request schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PathsRequest(BaseModel):
    paths: list[str] = Field(min_length=1, max_length=500)
    revision: str

    @field_validator("paths")
    @classmethod
    def unique_paths(cls, paths: list[str]) -> list[str]:
        if len(paths) != len(set(paths)):
            raise ValueError("paths must not contain duplicates")
        return paths


class SecurityScanRequest(BaseModel):
    source: Literal["staged"] = "staged"
    revision: str


class CommitGenerateRequest(BaseModel):
    source: Literal["staged"] = "staged"
    context: str | None = Field(default=None, max_length=2000)
    scan_id: str
    revision: str


class CommitCreateRequest(BaseModel):
    generation_id: str
    repository_revision: str
    selected_candidate: str = Field(default="standard", max_length=30)
    subject: str = Field(max_length=500)
    body: list[str] = Field(default_factory=list, max_length=20)
    footer: list[str] = Field(default_factory=list, max_length=10)
    confirmed: bool = False

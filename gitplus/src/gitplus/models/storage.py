"""Storage domain models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RepositoryRecord(BaseModel):
    id: str
    name: str
    root_path: str
    remote_url: str | None = None
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime | None = None


class CommitRecord(BaseModel):
    id: str
    repository_id: str
    commit_hash: str | None = None
    branch: str | None = None
    commit_type: str | None = None
    scope: str | None = None
    subject: str
    body: list[str] = Field(default_factory=list)
    summary: str | None = None
    files: list[str] = Field(default_factory=list)
    insertions: int = 0
    deletions: int = 0
    confidence: str | None = None
    confirmed_by_user: bool = False
    source_type: str = "generated_commit"
    selected_candidate: str | None = None
    should_split: bool = False
    split_confidence: float | None = None
    verification: list[str] = Field(default_factory=list)
    provider_name: str | None = None
    model_name: str | None = None
    content_hash: str | None = None
    security_summary: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class RiskRecord(BaseModel):
    id: str
    record_id: str
    record_type: str
    rule_id: str | None = None
    risk_level: str
    risk_type: str
    file_path: str | None = None
    line_number: int | None = None
    description: str
    masked_value: str | None = None
    suggestion: str | None = None
    blocks_remote_model: bool = False
    resolved: bool = False
    resolved_at: datetime | None = None
    created_at: datetime


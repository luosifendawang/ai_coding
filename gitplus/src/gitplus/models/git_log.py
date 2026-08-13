"""Git log models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GitCommitRecord(BaseModel):
    commit_hash: str
    short_hash: str
    author_name: str
    author_email: str
    authored_at: datetime
    committed_at: datetime
    subject: str
    body: str = ""
    parents: list[str] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    insertions: int = 0
    deletions: int = 0


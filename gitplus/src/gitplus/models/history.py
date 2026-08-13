"""History query models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CommitHistoryFilters(BaseModel):
    repository_id: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    commit_type: str | None = None
    confidence: str | None = None
    search: str | None = None
    confirmed_only: bool = False
    limit: int = 100
    offset: int = 0


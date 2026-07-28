"""Source reference models."""

from __future__ import annotations

from pydantic import BaseModel


class WeeklySourceReference(BaseModel):
    source_type: str
    source_id: str
    repository_id: str | None = None
    commit_hash: str | None = None
    title: str | None = None

    @property
    def label(self) -> str:
        if self.source_type == "commit" and self.commit_hash:
            return f"commit:{self.commit_hash[:8]}"
        return f"{self.source_type}:{self.source_id}"


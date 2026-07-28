"""Diagnostic result models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class DiagnosticStatus(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    SKIPPED = "skipped"


class DiagnosticItem(BaseModel):
    id: str
    name: str
    status: DiagnosticStatus
    message: str
    suggestion: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class DiagnosticReport(BaseModel):
    status: DiagnosticStatus
    items: list[DiagnosticItem]
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_items(cls, items: list[DiagnosticItem]) -> "DiagnosticReport":
        if any(item.status == DiagnosticStatus.FAIL for item in items):
            status = DiagnosticStatus.FAIL
        elif any(item.status == DiagnosticStatus.WARNING for item in items):
            status = DiagnosticStatus.WARNING
        else:
            status = DiagnosticStatus.PASS
        return cls(status=status, items=items)

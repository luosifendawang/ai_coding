"""Doctor command service."""

from __future__ import annotations

from gitplus.config import GitPlusConfig, default_config
from gitplus.diagnostics.checks import DiagnosticChecks
from gitplus.diagnostics.models import DiagnosticReport
from gitplus.storage.database import Database


class DoctorService:
    """Run gitplus diagnostics."""

    def __init__(self, config: GitPlusConfig | None = None, database: Database | None = None) -> None:
        self.config = config or default_config()
        self.database = database

    def run(self, *, check_ai: bool = False) -> DiagnosticReport:
        items = DiagnosticChecks(self.config, database=self.database).run(
            check_ai=check_ai,
        )
        return DiagnosticReport.from_items(items)

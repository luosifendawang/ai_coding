"""Doctor command service."""

from __future__ import annotations

from gitpulse.config import GitPulseConfig, default_config
from gitpulse.diagnostics.checks import DiagnosticChecks
from gitpulse.diagnostics.models import DiagnosticReport
from gitpulse.storage.database import Database


class DoctorService:
    """Run GitPulse diagnostics."""

    def __init__(self, config: GitPulseConfig | None = None, database: Database | None = None) -> None:
        self.config = config or default_config()
        self.database = database

    def run(self, *, check_ai: bool = False, check_feishu: bool = False) -> DiagnosticReport:
        items = DiagnosticChecks(self.config, database=self.database).run(
            check_ai=check_ai,
            check_feishu=check_feishu,
        )
        return DiagnosticReport.from_items(items)

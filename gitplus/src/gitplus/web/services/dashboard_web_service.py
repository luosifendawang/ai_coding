"""Dashboard summary data for the local Web console."""

from __future__ import annotations

from pathlib import Path

from gitplus.config import GitPlusConfig
from gitplus.storage.database import Database
from gitplus.storage.migrations.manager import CURRENT_SCHEMA_VERSION, MigrationManager
from gitplus.web.services.repository_web_service import RepositoryWebService


class DashboardWebService:
    def __init__(self, repository_service: RepositoryWebService, _repository_context: object, database: Database, config: GitPlusConfig) -> None:
        self.repository_service = repository_service
        self.database = database
        self.config = config

    def summary(self) -> dict[str, object]:
        status = self.repository_service.status()
        return {
            "repository": status["repository"],
            "git_summary": status["summary"],
            "repository_revision": status["revision"],
            "ai": {"provider": self.config.ai.provider, "model": self.config.ai.model, "configured": self.config.ai.provider == "mock" or bool(self.config.ai.api_key)},
            "database": self._database_status(),
            "warnings": [],
        }

    def _database_status(self) -> dict[str, object]:
        self.database.initialize()
        version = MigrationManager(self.database.engine).current_version()
        path = self.database.database_path
        return {"ok": version == CURRENT_SCHEMA_VERSION, "path": str(path), "schema_version": version, "expected_schema_version": CURRENT_SCHEMA_VERSION, "writable": path.parent.exists()}

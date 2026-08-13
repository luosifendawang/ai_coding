"""Storage service helpers."""

from __future__ import annotations

from pathlib import Path

from gitplus.config import StorageConfig
from gitplus.storage.database import Database


class StorageService:
    """Create configured database instances."""

    def __init__(self, config: StorageConfig | None = None) -> None:
        self.config = config or StorageConfig()

    def database(self, override_path: Path | None = None) -> Database:
        path = override_path or self.config.database_path
        db = Database(path, timeout_seconds=self.config.sqlite_timeout_seconds)
        if self.config.auto_initialize:
            db.initialize()
        return db


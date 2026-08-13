"""Local data management service."""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from gitplus.exceptions import DatabaseError
from gitplus.storage.database import Database
from gitplus.storage.migrations.manager import MigrationManager


@dataclass(frozen=True)
class DataInfo:
    database_path: Path
    database_size_bytes: int
    schema_version: int
    counts: dict[str, int]


class DataService:
    """Inspect, back up, and clear local SQLite data."""

    tables: Sequence[str] = (
        "repositories",
        "commit_records",
        "worklogs",
        "risks",
        "weekly_reports",
        "notification_records",
    )

    def __init__(self, database: Database) -> None:
        self.database = database

    def info(self) -> DataInfo:
        self.database.initialize()
        counts: dict[str, int] = {}
        with self.database.session_scope() as session:
            for table in self.tables:
                counts[table] = int(session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0)
        path = self.database.database_path
        return DataInfo(
            database_path=path,
            database_size_bytes=path.stat().st_size if path.exists() else 0,
            schema_version=MigrationManager(self.database.engine).current_version(),
            counts=counts,
        )

    def backup(self, output_dir: Path | None = None) -> Path:
        self.database.initialize()
        source = self.database.database_path
        target_dir = output_dir or source.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        target = target_dir / f"gitplus-backup-{stamp}.db"
        shutil.copy2(source, target)
        return target

    def clear(self, *, create_backup: bool = True) -> Path | None:
        backup_path = self.backup() if create_backup else None
        with self.database.session_scope() as session:
            for table in reversed(self.tables):
                session.execute(text(f"DELETE FROM {table}"))
        return backup_path

    def validate_sqlite(self, path: Path) -> None:
        if not path.exists():
            raise DatabaseError(f"备份文件不存在：{path}")
        try:
            with sqlite3.connect(path) as connection:
                result = connection.execute("PRAGMA integrity_check").fetchone()
        except sqlite3.DatabaseError as exc:
            raise DatabaseError("备份文件不是有效 SQLite 数据库。") from exc
        if not result or result[0] != "ok":
            raise DatabaseError("SQLite 完整性检查失败。")

"""Minimal sequential migration manager."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.orm import Session

from gitplus.exceptions import DatabaseMigrationError
from gitplus.storage.orm_models import Base, MigrationORM

CURRENT_SCHEMA_VERSION = 6


@dataclass(frozen=True)
class Migration:
    version: int
    name: str


MIGRATIONS = [
    Migration(version=1, name="initial_schema"),
    Migration(version=2, name="notification_audit_fields"),
    Migration(version=3, name="web_operation_audits"),
    Migration(version=4, name="worklog_history_fields"),
    Migration(version=5, name="notification_delivery_fields"),
    # Compatibility marker for databases created while scheduled delivery existed.
    # The feature has been removed, but existing local databases must remain readable.
    Migration(version=6, name="smart_weekly_delivery"),
]


class MigrationManager:
    """Apply simple ordered SQLAlchemy metadata migrations."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def migrate(self) -> None:
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            current = self.current_version(session)
            if current > CURRENT_SCHEMA_VERSION:
                raise DatabaseMigrationError("数据库版本高于当前应用支持版本。")
            for migration in MIGRATIONS:
                if migration.version > current:
                    self._apply_migration(migration)
                    session.add(
                        MigrationORM(version=migration.version, name=migration.name)
                    )
            session.commit()

    def current_version(self, session: Session | None = None) -> int:
        owns_session = session is None
        active_session = session or Session(self.engine)
        try:
            version = active_session.execute(
                select(MigrationORM.version).order_by(MigrationORM.version.desc())
            ).scalar()
            return int(version or 0)
        finally:
            if owns_session:
                active_session.close()

    def _apply_migration(self, migration: Migration) -> None:
        if migration.version == 2:
            self._add_notification_audit_columns()
        elif migration.version == 4:
            self._add_worklog_history_columns()
        elif migration.version == 5:
            self._add_notification_delivery_columns()

    def _add_notification_audit_columns(self) -> None:
        inspector = inspect(self.engine)
        if "notification_records" not in inspector.get_table_names():
            return
        columns = {
            column["name"] for column in inspector.get_columns("notification_records")
        }
        additions = {
            "payload_summary": "TEXT",
            "byte_size": "INTEGER NOT NULL DEFAULT 0",
            "truncated": "INTEGER NOT NULL DEFAULT 0",
            "removed_sections_json": "TEXT",
            "attempt_count": "INTEGER NOT NULL DEFAULT 0",
            "http_status": "INTEGER",
            "request_id": "TEXT",
            "error_type": "TEXT",
            "error_message": "TEXT",
            "forced": "INTEGER NOT NULL DEFAULT 0",
            "updated_at": "DATETIME",
        }
        with self.engine.begin() as connection:
            for name, sql_type in additions.items():
                if name not in columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE notification_records ADD COLUMN {name} {sql_type}"
                        )
                    )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_notification_content_hash "
                    "ON notification_records(content_hash)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_notification_status ON notification_records(status)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_notification_sent_at ON notification_records(sent_at)"
                )
            )

    def _add_worklog_history_columns(self) -> None:
        inspector = inspect(self.engine)
        if "worklogs" not in inspector.get_table_names():
            return
        columns = {column["name"] for column in inspector.get_columns("worklogs")}
        additions = {
            "occurred_at": "DATETIME",
            "related_commit_hash": "VARCHAR",
            "source": "VARCHAR NOT NULL DEFAULT 'manual'",
        }
        with self.engine.begin() as connection:
            for name, sql_type in additions.items():
                if name not in columns:
                    connection.execute(
                        text(f"ALTER TABLE worklogs ADD COLUMN {name} {sql_type}")
                    )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_worklogs_occurred_at "
                    "ON worklogs(occurred_at)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_worklogs_related_commit_hash "
                    "ON worklogs(related_commit_hash)"
                )
            )

    def _add_notification_delivery_columns(self) -> None:
        inspector = inspect(self.engine)
        if "notification_records" not in inspector.get_table_names():
            return
        columns = {
            column["name"] for column in inspector.get_columns("notification_records")
        }
        additions = {
            "report_version": "INTEGER NOT NULL DEFAULT 1",
            "provider_mode": "VARCHAR NOT NULL DEFAULT 'app'",
            "target_digest": "VARCHAR",
            "feishu_message_id": "VARCHAR",
        }
        with self.engine.begin() as connection:
            for name, sql_type in additions.items():
                if name not in columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE notification_records ADD COLUMN {name} {sql_type}"
                        )
                    )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_notification_target_digest "
                    "ON notification_records(target_digest)"
                )
            )

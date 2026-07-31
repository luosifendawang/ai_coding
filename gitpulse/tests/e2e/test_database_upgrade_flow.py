import sqlite3
from pathlib import Path

from gitpulse.storage.database import Database
from gitpulse.storage.migrations.manager import CURRENT_SCHEMA_VERSION, MigrationManager


def test_database_v1_notification_table_upgrades_to_current(tmp_path: Path) -> None:
    db_path = tmp_path / "old.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at DATETIME NOT NULL)")
        connection.execute("INSERT INTO migrations(version, name, applied_at) VALUES (1, 'initial_schema', '2026-01-01T00:00:00')")
        connection.execute(
            "CREATE TABLE notification_records ("
            "id TEXT PRIMARY KEY, report_id TEXT NOT NULL, channel TEXT NOT NULL, "
            "message_type TEXT NOT NULL, status TEXT NOT NULL, response_code TEXT, "
            "response_message TEXT, content_hash TEXT, sent_at TEXT, created_at DATETIME NOT NULL)"
        )

    database = Database(db_path)
    database.initialize()

    assert MigrationManager(database.engine).current_version() == CURRENT_SCHEMA_VERSION
    with sqlite3.connect(db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(notification_records)")}
    assert "payload_summary" in columns
    assert "updated_at" in columns
    database.dispose()


def test_database_v3_worklogs_upgrade_preserves_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "v3.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "CREATE TABLE migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at DATETIME NOT NULL)"
        )
        for version, name in [
            (1, "initial_schema"),
            (2, "notification_audit_fields"),
            (3, "web_operation_audits"),
        ]:
            connection.execute(
                "INSERT INTO migrations(version, name, applied_at) VALUES (?, ?, '2026-01-01T00:00:00')",
                (version, name),
            )
        connection.execute(
            "CREATE TABLE worklogs ("
            "id TEXT PRIMARY KEY, repository_id TEXT, work_date DATE NOT NULL, "
            "work_type TEXT NOT NULL, title TEXT NOT NULL, description TEXT, "
            "result TEXT, duration_minutes INTEGER, tags_json TEXT, "
            "confirmed_by_user INTEGER, created_at DATETIME NOT NULL, "
            "updated_at DATETIME NOT NULL)"
        )
        connection.execute(
            "INSERT INTO worklogs VALUES ("
            "'worklog_old', NULL, '2026-07-01', 'debug', '旧记录', NULL, "
            "NULL, 30, '[]', 1, '2026-07-01', '2026-07-01')"
        )

    database = Database(db_path)
    database.initialize()

    with sqlite3.connect(db_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(worklogs)")
        }
        row = connection.execute(
            "SELECT title, source FROM worklogs WHERE id = 'worklog_old'"
        ).fetchone()
    assert {"occurred_at", "related_commit_hash", "source"}.issubset(columns)
    assert row == ("旧记录", "manual")
    database.dispose()

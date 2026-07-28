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

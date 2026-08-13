from pathlib import Path

from sqlalchemy import select

from gitplus.storage.database import Database
from gitplus.storage.migrations.manager import CURRENT_SCHEMA_VERSION, MigrationManager
from gitplus.storage.orm_models import MigrationORM, RepositoryORM


def test_database_initialize_creates_parent_and_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "gitplus.db"
    database = Database(db_path)

    database.initialize()

    assert db_path.exists()
    assert database.foreign_keys_enabled() is True
    with database.session_scope() as session:
        versions = session.execute(select(MigrationORM.version)).scalars().all()
        assert max(versions) == CURRENT_SCHEMA_VERSION
    database.dispose()


def test_database_initialize_is_idempotent(tmp_path: Path) -> None:
    database = Database(tmp_path / "gitplus.db")

    database.initialize()
    database.initialize()

    with database.session_scope() as session:
        versions = session.execute(select(MigrationORM.version)).scalars().all()
        assert versions == list(range(1, CURRENT_SCHEMA_VERSION + 1))
    database.dispose()


def test_session_scope_rolls_back_on_error(tmp_path: Path) -> None:
    database = Database(tmp_path / "gitplus.db")
    database.initialize()

    try:
        with database.session_scope() as session:
            session.add(RepositoryORM(id="repo_test", name="repo", root_path="/tmp/repo"))
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    with database.session_scope() as session:
        assert session.get(RepositoryORM, "repo_test") is None
    database.dispose()


def test_migration_manager_reports_current_version(tmp_path: Path) -> None:
    database = Database(tmp_path / "gitplus.db")
    database.initialize()

    assert MigrationManager(database.engine).current_version() == CURRENT_SCHEMA_VERSION
    database.dispose()

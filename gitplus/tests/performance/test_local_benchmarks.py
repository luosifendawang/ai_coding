import time as time_module
from pathlib import Path

from gitplus.storage.database import Database
from gitplus.storage.migrations.manager import MigrationManager


def test_database_initialize_under_basic_threshold(tmp_path: Path) -> None:
    start = time_module.perf_counter()
    database = Database(tmp_path / "perf.db")
    database.initialize()
    version = MigrationManager(database.engine).current_version()
    elapsed = time_module.perf_counter() - start

    assert version >= 1
    assert elapsed < 5
    database.dispose()

from pathlib import Path

from gitplus.models.storage import RepositoryRecord
from gitplus.services.data_service import DataService
from gitplus.storage.database import Database
from gitplus.storage.orm_models import utc_now
from gitplus.storage.unit_of_work import UnitOfWork


def test_data_service_info_backup_and_clear(tmp_path: Path) -> None:
    database = Database(tmp_path / "data.db")
    database.initialize()
    current = utc_now()
    with UnitOfWork(database) as uow:
        uow.repositories.upsert(
            RepositoryRecord(
                id="repo_1",
                name="repo",
                root_path=str(tmp_path / "repo"),
                created_at=current,
                updated_at=current,
            )
        )

    service = DataService(database)
    info = service.info()
    backup = service.backup(tmp_path)
    clear_backup = service.clear()
    after = service.info()

    assert info.counts["repositories"] == 1
    assert backup.exists()
    assert clear_backup is not None and clear_backup.exists()
    assert after.counts["repositories"] == 0
    database.dispose()

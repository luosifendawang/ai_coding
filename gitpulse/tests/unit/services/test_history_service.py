from datetime import datetime, timezone
from pathlib import Path

import pytest

from gitpulse.models.history import CommitHistoryFilters
from gitpulse.models.storage import CommitRecord, RepositoryRecord
from gitpulse.services.history_service import HistoryService
from gitpulse.storage.database import Database
from gitpulse.storage.unit_of_work import UnitOfWork


@pytest.fixture()
def database(tmp_path: Path) -> Database:
    db = Database(tmp_path / "test.db")
    db.initialize()
    yield db
    db.dispose()


def test_history_service_lists_and_gets_commit_records(database: Database) -> None:
    current = datetime.now(timezone.utc)
    with UnitOfWork(database) as uow:
        repo = uow.repositories.upsert(
            RepositoryRecord(id="repo_1", name="repo", root_path=str(Path("/tmp/repo")), created_at=current, updated_at=current)
        )
        uow.commit_records.create(
            CommitRecord(
                id="record_1",
                repository_id=repo.id,
                commit_type="fix",
                subject="fix: 修复问题",
                confirmed_by_user=True,
                created_at=current,
                updated_at=current,
            )
        )

    service = HistoryService(database)
    listed = service.list_commit_records(CommitHistoryFilters(repository_id="repo_1", commit_type="fix"))
    fetched = service.get_commit_record("record_1")

    assert listed[0].id == "record_1"
    assert fetched.subject == "fix: 修复问题"


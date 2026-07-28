from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from gitpulse.models.storage import CommitRecord, RepositoryRecord, RiskRecord
from gitpulse.models.worklog import Worklog, WorklogFilters, WorklogUpdate
from gitpulse.storage.database import Database
from gitpulse.storage.repositories import CommitRecordRepository, RepositoryRepository, RiskRepository, WorklogRepository
from gitpulse.storage.unit_of_work import UnitOfWork


@pytest.fixture()
def database(tmp_path: Path) -> Database:
    db = Database(tmp_path / "test.db")
    db.initialize()
    yield db
    db.dispose()


def now() -> datetime:
    return datetime.now(timezone.utc)


def repo_record(root: str = "/tmp/repo") -> RepositoryRecord:
    current = now()
    return RepositoryRecord(id="repo_1", name="repo", root_path=root, remote_url="https://user:pass@example.test/repo.git", created_at=current, updated_at=current)


def test_repository_upsert_and_sanitize_remote(database: Database) -> None:
    with database.session_scope() as session:
        repo = RepositoryRepository(session).upsert(repo_record())
        same = RepositoryRepository(session).upsert(repo_record())

    assert repo.id == same.id
    assert "user:pass" not in (same.remote_url or "")
    assert same.remote_url == "https://example.test/repo.git"


def test_commit_record_repository_create_and_query(database: Database) -> None:
    current = now()
    with database.session_scope() as session:
        repo = RepositoryRepository(session).upsert(repo_record())
        record = CommitRecordRepository(session).create(
            CommitRecord(
                id="record_1",
                repository_id=repo.id,
                branch="main",
                commit_type="fix",
                scope="usb",
                subject="fix(usb): 修复资源释放问题",
                body=["清理连接对象"],
                files=["src/usb.py"],
                insertions=2,
                deletions=1,
                confidence="high",
                confirmed_by_user=True,
                selected_candidate="standard",
                provider_name="mock",
                model_name="mock-model",
                security_summary={"high": 0},
                created_at=current,
                updated_at=current,
            )
        )
        fetched = CommitRecordRepository(session).get_by_id(record.id)
        listed = CommitRecordRepository(session).list_by_repository(repo.id, confirmed_only=True)

    assert fetched is not None
    assert fetched.body == ["清理连接对象"]
    assert fetched.files == ["src/usb.py"]
    assert listed[0].subject.startswith("fix")


def test_risk_repository_stores_masked_values(database: Database) -> None:
    current = now()
    with database.session_scope() as session:
        risks = RiskRepository(session).create_many(
            [
                RiskRecord(
                    id="risk_1",
                    record_id="record_1",
                    record_type="commit",
                    rule_id="openai_api_key",
                    risk_level="high",
                    risk_type="secret",
                    description="检测到 API Key",
                    masked_value="<API_KEY_1>",
                    suggestion="移到环境变量",
                    blocks_remote_model=True,
                    created_at=current,
                )
            ]
        )
        listed = RiskRepository(session).list_by_record("record_1", "commit")

    assert risks[0].masked_value == "<API_KEY_1>"
    assert listed[0].masked_value == "<API_KEY_1>"


def test_worklog_repository_crud_and_filters(database: Database) -> None:
    current = now()
    with database.session_scope() as session:
        repo = RepositoryRepository(session).upsert(repo_record())
        repository = WorklogRepository(session)
        created = repository.create(
            Worklog(
                id="worklog_1",
                repository_id=repo.id,
                work_date=date(2026, 7, 27),
                work_type="debug",
                title="排查 ADB 问题",
                result="恢复连接",
                duration_minutes=90,
                tags=["adb", "usb"],
                created_at=current,
                updated_at=current,
            )
        )
        updated = repository.update(created.id, WorklogUpdate(duration_minutes=120, tags=["adb"]))
        listed = repository.list(WorklogFilters(repository_id=repo.id, tags=["adb"]))
        deleted = repository.delete(created.id)

    assert updated.duration_minutes == 120
    assert updated.tags == ["adb"]
    assert listed[0].id == "worklog_1"
    assert deleted is True


def test_unit_of_work_rolls_back_all_repositories(database: Database) -> None:
    with pytest.raises(RuntimeError):
        with UnitOfWork(database) as uow:
            uow.repositories.upsert(repo_record())
            raise RuntimeError("fail")

    with database.session_scope() as session:
        assert RepositoryRepository(session).get_by_id("repo_1") is None


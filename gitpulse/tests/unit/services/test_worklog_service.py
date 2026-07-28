from datetime import date
from pathlib import Path

import pytest

from gitpulse.exceptions import RecordNotFoundError, SensitiveContentError
from gitpulse.models.worklog import WorklogCreate, WorklogFilters, WorklogUpdate
from gitpulse.services.worklog_service import WorklogService
from gitpulse.storage.database import Database


@pytest.fixture()
def database(tmp_path: Path) -> Database:
    db = Database(tmp_path / "test.db")
    db.initialize()
    yield db
    db.dispose()


def test_worklog_service_create_update_list_delete(database: Database) -> None:
    service = WorklogService(database)
    created = service.create(
        WorklogCreate(
            work_date=date(2026, 7, 27),
            work_type="debug",
            title="排查 ADB 问题",
            result="恢复",
            duration_minutes=90,
            tags=[" adb ", "adb", "usb"],
        )
    )

    assert created.tags == ["adb", "usb"]
    updated = service.update(created.id, WorklogUpdate(duration_minutes=120))
    listed = service.list(WorklogFilters(work_types=["debug"], tags=["adb"]))

    assert updated.duration_minutes == 120
    assert listed[0].id == created.id
    service.delete(created.id)
    with pytest.raises(RecordNotFoundError):
        service.get(created.id)


def test_worklog_service_blocks_high_risk_secret(database: Database) -> None:
    service = WorklogService(database)

    with pytest.raises(SensitiveContentError):
        service.create(
            WorklogCreate(
                work_date=date(2026, 7, 27),
                work_type="debug",
                title="排查问题",
                result="token sk-testexample1234567890abcdef",
            )
        )


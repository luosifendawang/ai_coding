from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import pytest

from gitplus.exceptions import RepositoryOperationError
from gitplus.models.notification import NotificationRecord
from gitplus.models.source import WeeklySourceReference
from gitplus.models.weekly import (
    WeeklyDateRange,
    WeeklyReport,
    WeeklyReportItem,
    WeeklyReportTopic,
)
from gitplus.storage.database import Database
from gitplus.storage.unit_of_work import UnitOfWork


@pytest.fixture()
def database(tmp_path: Path) -> Database:
    db = Database(tmp_path / "test.db")
    db.initialize()
    yield db
    db.dispose()


def notification(now: datetime) -> NotificationRecord:
    return NotificationRecord(
        id="notification_1",
        report_id="weekly_1",
        channel="feishu",
        message_type="interactive",
        status="pending",
        content_hash="hash",
        created_at=now,
        updated_at=now,
    )


def report() -> WeeklyReport:
    now = datetime.now(timezone.utc)
    item = WeeklyReportItem(
        id="item_1",
        content="修复设备断开后的资源释放问题",
        confidence="high",
        confirmed_by_user=True,
        sources=[WeeklySourceReference(source_type="commit", source_id="abcdef123456", commit_hash="abcdef123456")],
    )
    return WeeklyReport(
        id="weekly_1",
        title="本周开发周报",
        date_range=WeeklyDateRange(
            date_from=date(2026, 7, 27),
            date_to=date(2026, 8, 2),
            datetime_from=datetime.combine(date(2026, 7, 27), time.min, timezone.utc),
            datetime_to=datetime.combine(date(2026, 8, 2), time.max, timezone.utc),
            timezone="UTC",
            label="本周",
        ),
        completed=[
            WeeklyReportTopic(
                id="topic_1",
                title="USB 设备异常断开处理",
                category="completed",
                confidence="high",
                confirmed_by_user=True,
                items=[item],
                sources=item.sources,
            )
        ],
        source_coverage=1,
        status="confirmed",
        content_markdown="# report",
        generator="rule_based",
        created_at=now,
        updated_at=now,
        confirmed_at=now,
    )


def test_notification_repository_status_and_duplicate_query(database: Database) -> None:
    now = datetime.now(timezone.utc)
    with UnitOfWork(database) as uow:
        uow.weekly_reports.create(report())
        created = uow.notifications.create(notification(now))
        sent = uow.notifications.update_status(created.id, status="previewed")
        sent = uow.notifications.update_status(sent.id, status="confirmed")
        sent = uow.notifications.update_status(sent.id, status="sending")
        sent = uow.notifications.update_status(sent.id, status="sent", sent_at=now)
        found = uow.notifications.find_recent_by_hash("hash", channel="feishu", since=now - timedelta(hours=1))

    assert sent.status == "sent"
    assert found[0].id == "notification_1"


def test_notification_repository_rejects_illegal_transition(database: Database) -> None:
    now = datetime.now(timezone.utc)
    with pytest.raises(RepositoryOperationError), UnitOfWork(database) as uow:
        uow.weekly_reports.create(report())
        created = uow.notifications.create(notification(now))
        uow.notifications.update_status(created.id, status="sent")

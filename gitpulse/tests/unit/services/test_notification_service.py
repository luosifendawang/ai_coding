from __future__ import annotations

from datetime import date, datetime, time, timezone
from pathlib import Path

import pytest

from gitpulse.config import FeishuConfig
from gitpulse.exceptions import (
    NotificationConfirmationError,
    NotificationValidationError,
)
from gitpulse.models.feishu import FeishuSendResponse
from gitpulse.models.source import WeeklySourceReference
from gitpulse.models.weekly import (
    WeeklyDateRange,
    WeeklyReport,
    WeeklyReportItem,
    WeeklyReportTopic,
)
from gitpulse.services.notification_service import NotificationService
from gitpulse.storage.database import Database
from gitpulse.storage.unit_of_work import UnitOfWork


class FakeFeishuClient:
    def __init__(self) -> None:
        self.payloads = []

    def send_payload(self, payload):
        self.payloads.append(payload)
        return FeishuSendResponse(success=True, http_status=200, code=0, message="success", request_id="req")

    def test_connection(self):
        return FeishuSendResponse(success=True, http_status=200, code=0, message="success")


@pytest.fixture()
def database(tmp_path: Path) -> Database:
    db = Database(tmp_path / "test.db")
    db.initialize()
    yield db
    db.dispose()


def save_report(database: Database, status: str = "confirmed") -> str:
    item = report()
    item.status = status
    with UnitOfWork(database) as uow:
        uow.weekly_reports.create(item)
    return item.id


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


def test_notification_service_requires_confirmed_report(database: Database) -> None:
    report_id = save_report(database, status="draft")
    service = NotificationService(database, feishu_config=FeishuConfig(signature_required=False))

    with pytest.raises(NotificationValidationError):
        service.preview_weekly(report_id)


def test_notification_service_requires_explicit_confirmation(database: Database) -> None:
    report_id = save_report(database)
    service = NotificationService(database, feishu_config=FeishuConfig(signature_required=False))

    with pytest.raises(NotificationConfirmationError):
        service.send_weekly(report_id, confirmed=False)


def test_notification_service_sends_and_records_success(database: Database, monkeypatch) -> None:
    report_id = save_report(database)
    fake = FakeFeishuClient()
    monkeypatch.setenv("GITPULSE_FEISHU_WEBHOOK", "https://open.feishu.cn/open-apis/bot/v2/hook/abcd")
    service = NotificationService(
        database,
        feishu_config=FeishuConfig(signature_required=False),
        client_factory=lambda *_args: fake,
    )

    result = service.send_weekly(report_id, confirmed=True)

    assert result.record.status == "sent"
    assert result.record.request_id == "req"
    assert fake.payloads[0]["msg_type"] == "interactive"

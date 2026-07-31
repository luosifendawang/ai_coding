from __future__ import annotations

import subprocess
from datetime import date, datetime, time, timezone
from pathlib import Path

import httpx
import pytest

pytest.importorskip("fastapi")

from gitpulse.config import FeishuConfig
from gitpulse.models.feishu import FeishuSendResponse
from gitpulse.models.source import WeeklySourceReference
from gitpulse.models.weekly import (
    WeeklyDateRange,
    WeeklyReport,
    WeeklyReportItem,
    WeeklyReportTopic,
)
from gitpulse.storage.database import Database
from gitpulse.storage.unit_of_work import UnitOfWork
from gitpulse.web.app import create_app


class FakeFeishuClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.payloads: list[dict[str, object]] = []

    def test_connection(self, *, send_message: bool = False) -> FeishuSendResponse:
        return FeishuSendResponse(
            success=True,
            http_status=200,
            code=0,
            message="ok",
            request_id="test_req",
        )

    def send_payload(self, payload: dict[str, object]) -> FeishuSendResponse:
        self.payloads.append(payload)
        if self.fail:
            return FeishuSendResponse(
                success=False,
                http_status=400,
                code=999,
                message="failed",
            )
        return FeishuSendResponse(
            success=True,
            http_status=200,
            code=0,
            message="ok",
            request_id="send_req",
            raw_metadata={"message_id": "om_test_message"},
        )


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def report() -> WeeklyReport:
    now = datetime.now(timezone.utc)
    source = WeeklySourceReference(
        source_type="commit",
        source_id="abcdef123456",
        commit_hash="abcdef123456",
    )
    item = WeeklyReportItem(
        id="item_1",
        content="完成飞书通知中心",
        confidence="high",
        confirmed_by_user=True,
        sources=[source],
    )
    return WeeklyReport(
        id="weekly_notify_1",
        title="飞书通知周报",
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
                title="飞书通知中心",
                category="completed",
                confidence="high",
                confirmed_by_user=True,
                items=[item],
                sources=[source],
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


async def authenticated_client(
    tmp_path: Path, *, fail: bool = False
) -> tuple[httpx.AsyncClient, object, dict[str, str], FakeFeishuClient]:
    project = tmp_path / "repo"
    project.mkdir()
    git(project, "init")
    git(project, "config", "user.name", "Test User")
    git(project, "config", "user.email", "test@example.com")
    app = create_app(
        project,
        access_token="fixed-token",
        user_config_path=tmp_path / "user" / "config.yml",
        secrets_path=tmp_path / "user" / "secrets.yml",
        database=Database(tmp_path / "gitpulse.db"),
    )
    fake = FakeFeishuClient(fail=fail)
    app.state.notification_web_service.config = FeishuConfig(
        enabled=True,
        mode="app",
        app_id="cli_testapp1234",
        app_secret="test-secret",
        receive_id="oc_test_chat",
    )
    app.state.notification_web_service.client_factory = lambda *_args: fake
    repository = app.state.notification_web_service.repository_context.ensure_record()
    with UnitOfWork(app.state.database) as uow:
        uow.weekly_reports.create(report(), repository_id=repository.id)
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1:8765",
    )
    await client.get("/auth/local?token=fixed-token", follow_redirects=False)
    session_id = client.cookies.get("gitpulse_session")
    csrf = app.state.sessions.get(session_id).csrf_token
    return (
        client,
        app,
        {"origin": "http://127.0.0.1:8765", "x-csrf-token": csrf},
        fake,
    )


@pytest.mark.anyio
async def test_notification_preview_send_duplicate_and_retry(tmp_path: Path) -> None:
    client, app, headers, fake = await authenticated_client(tmp_path)
    try:
        status = await client.get("/api/notifications/config-status")
        assert status.status_code == 200
        body = status.json()
        assert body["valid"] is True
        assert "test-secret" not in status.text

        preview = await client.post(
            "/api/notifications/preview",
            json={"report_id": "weekly_notify_1", "message_type": "interactive"},
            headers=headers,
        )
        assert preview.status_code == 200, preview.text
        assert preview.json()["payload"]["msg_type"] == "interactive"
        assert "test-secret" not in preview.text

        sent = await client.post(
            "/api/notifications/send",
            json={
                "report_id": "weekly_notify_1",
                "message_type": "interactive",
                "confirmed": True,
            },
            headers=headers,
        )
        assert sent.status_code == 200, sent.text
        assert sent.json()["record"]["status"] == "sent"
        assert sent.json()["record"]["feishu_message_id"] == "om_test_message"
        assert len(fake.payloads) == 1

        duplicate = await client.post(
            "/api/notifications/send",
            json={
                "report_id": "weekly_notify_1",
                "message_type": "interactive",
                "confirmed": True,
            },
            headers=headers,
        )
        assert duplicate.status_code == 200
        assert duplicate.json()["record"]["status"] == "duplicate_blocked"
        assert duplicate.json()["message"] == "该版本周报已发送到相同目标。"

        forced = await client.post(
            "/api/notifications/send",
            json={
                "report_id": "weekly_notify_1",
                "message_type": "interactive",
                "confirmed": True,
                "allow_duplicate": True,
            },
            headers=headers,
        )
        assert forced.status_code == 200
        assert forced.json()["record"]["status"] == "sent"
        assert len(fake.payloads) == 2

        app.state.notification_web_service.client_factory = lambda *_args: FakeFeishuClient(
            fail=True
        )
        failed = await client.post(
            "/api/notifications/send",
            json={
                "report_id": "weekly_notify_1",
                "message_type": "text",
                "confirmed": True,
            },
            headers=headers,
        )
        assert failed.status_code == 200
        assert failed.json()["record"]["status"] == "failed"

        app.state.notification_web_service.client_factory = lambda *_args: fake
        retry = await client.post(
            f"/api/notifications/{failed.json()['record']['id']}/retry",
            json={"confirmed": True},
            headers=headers,
        )
        assert retry.status_code == 200, retry.text
        assert retry.json()["record"]["status"] == "sent"
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_notification_pages_require_session_and_render(tmp_path: Path) -> None:
    client, _app, _headers, _fake = await authenticated_client(tmp_path)
    try:
        assert (await client.get("/notifications")).status_code == 200
        index = await client.get("/notifications")
        detail = await client.get("/notifications/example")
    finally:
        await client.aclose()
    assert "周报发送中心" in index.text
    assert "notifications.js" in index.text
    assert "发送记录" in detail.text
    assert "notification-detail.js" in detail.text

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

pytest.importorskip("fastapi")

from gitpulse.ai.mock_provider import MockLLMProvider
from gitpulse.config import FeishuConfig
from gitpulse.models.feishu import FeishuSendResponse
from gitpulse.storage.database import Database
from gitpulse.storage.unit_of_work import UnitOfWork
from gitpulse.web.app import create_app


class FakeFeishuClient:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def test_connection(self, *, send_message: bool = False) -> FeishuSendResponse:
        return FeishuSendResponse(success=True, http_status=200, code=0, message="ok")

    def send_payload(self, payload: dict[str, object]) -> FeishuSendResponse:
        self.payloads.append(payload)
        return FeishuSendResponse(
            success=True,
            http_status=200,
            code=0,
            message="ok",
            request_id="req_full_flow",
            raw_metadata={"message_id": "om_full_flow"},
        )


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.mark.anyio
async def test_full_web_commit_worklog_weekly_notification_flow(
    tmp_path: Path,
) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    git(project, "init")
    git(project, "config", "user.name", "Test User")
    git(project, "config", "user.email", "test@example.com")
    (project / "README.md").write_text("start\n", encoding="utf-8")
    git(project, "add", "--", "README.md")
    git(project, "commit", "-m", "chore: initialize")
    (project / "feature.py").write_text("enabled = True\n", encoding="utf-8")
    database = Database(tmp_path / "gitpulse.db")
    app = create_app(
        project,
        access_token="fixed-token",
        user_config_path=tmp_path / "user" / "config.yml",
        secrets_path=tmp_path / "user" / "secrets.yml",
        database=database,
        commit_provider=MockLLMProvider(),
    )
    fake = FakeFeishuClient()
    app.state.notification_web_service.config = FeishuConfig(
        enabled=True,
        mode="app",
        app_id="cli_testapp1234",
        app_secret="test-secret",
        receive_id="oc_test_chat",
    )
    app.state.notification_web_service.client_factory = lambda *_args: fake
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1:8765",
    ) as client:
        await client.get("/auth/local?token=fixed-token", follow_redirects=False)
        session_id = client.cookies.get("gitpulse_session")
        csrf = app.state.sessions.get(session_id).csrf_token
        headers = {"origin": "http://127.0.0.1:8765", "x-csrf-token": csrf}

        status = (await client.get("/api/repository/status")).json()
        staged = await client.post(
            "/api/repository/stage",
            json={"paths": ["feature.py"], "revision": status["revision"]},
            headers=headers,
        )
        assert staged.status_code == 200
        revision = staged.json()["revision"]

        scan = await client.post(
            "/api/repository/security-scan",
            json={"source": "staged", "revision": revision},
            headers=headers,
        )
        assert scan.status_code == 200
        generated = await client.post(
            "/api/repository/commit/generate",
            json={
                "source": "staged",
                "scan_id": scan.json()["scan_id"],
                "revision": revision,
                "context": "新增功能开关",
            },
            headers=headers,
        )
        assert generated.status_code == 200
        committed = await client.post(
            "/api/repository/commit",
            json={
                "generation_id": generated.json()["generation_id"],
                "repository_revision": revision,
                "selected_candidate": "standard",
                "subject": "feat(core): 增加功能开关",
                "body": ["增加本地功能开关配置"],
                "confirmed": True,
            },
            headers=headers,
        )
        assert committed.status_code == 200

        worklog = await client.post(
            "/api/worklogs",
            json={
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "type": "development",
                "title": "完成 Web 全流程验收",
                "result": "Commit、周报和飞书通知连通",
                "duration_minutes": 45,
                "tags": ["release"],
            },
            headers=headers,
        )
        assert worklog.status_code == 201

        weekly = await client.post(
            "/api/weekly/generate",
            json={
                "range_kind": "custom",
                "date_from": "2020-01-01",
                "date_to": "2030-01-01",
                "authors": ["test@example.com"],
                "include_uncommitted": False,
                "use_ai": False,
                "excluded_source_ids": [],
                "user_context": "",
            },
            headers=headers,
        )
        assert weekly.status_code == 201, weekly.text
        report = weekly.json()["report"]
        confirmed = await client.post(
            f"/api/weekly/{report['id']}/confirm",
            json={"version": report["version"]},
            headers=headers,
        )
        assert confirmed.status_code == 200, confirmed.text
        send = await client.post(
            "/api/notifications/send",
            json={
                "report_id": report["id"],
                "message_type": "interactive",
                "confirmed": True,
            },
            headers=headers,
        )
        assert send.status_code == 200, send.text
        assert send.json()["record"]["status"] == "sent"

    assert git(project, "log", "-1", "--pretty=%s") == "feat(core): 增加功能开关"
    assert len(fake.payloads) == 1
    with UnitOfWork(database) as uow:
        records = uow.notifications.list(channel="feishu")
        assert records[0].status == "sent"
        assert records[0].feishu_message_id == "om_full_flow"

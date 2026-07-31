from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

pytest.importorskip("fastapi")

from gitpulse.models.storage import CommitRecord
from gitpulse.storage.database import Database
from gitpulse.storage.unit_of_work import UnitOfWork
from gitpulse.web.app import create_app


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


async def authenticated_client(
    tmp_path: Path,
) -> tuple[httpx.AsyncClient, object, dict[str, str], Path]:
    project = tmp_path / "repo"
    project.mkdir()
    git(project, "init")
    git(project, "config", "user.name", "Test User")
    git(project, "config", "user.email", "test@example.com")
    (project / "README.md").write_text("start\n", encoding="utf-8")
    git(project, "add", "--", "README.md")
    git(project, "commit", "-m", "feat(core): initialize history")
    app = create_app(
        project,
        access_token="fixed-token",
        user_config_path=tmp_path / "user" / "config.yml",
        secrets_path=tmp_path / "user" / "secrets.yml",
        database=Database(tmp_path / "gitpulse.db"),
    )
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
        {
            "origin": "http://127.0.0.1:8765",
            "x-csrf-token": csrf,
        },
        project,
    )


@pytest.mark.anyio
async def test_worklog_crud_filter_copy_fields_and_confirmation(
    tmp_path: Path,
) -> None:
    client, _app, headers, _project = await authenticated_client(tmp_path)
    payload = {
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "type": "development",
        "title": "实现历史查询",
        "description": "聚合本地记录",
        "result": "API 可用",
        "duration_minutes": 75,
        "tags": ["backend", "history"],
        "related_commit_hash": "abcdef1",
        "source": "manual",
    }

    assert (await client.post("/api/worklogs", json=payload)).status_code == 403
    invalid = await client.post(
        "/api/worklogs",
        json={**payload, "duration_minutes": 0},
        headers=headers,
    )
    assert invalid.status_code == 422
    created = await client.post("/api/worklogs", json=payload, headers=headers)
    assert created.status_code == 201
    worklog_id = created.json()["id"]

    listed = await client.get(
        "/api/worklogs",
        params={"type": "development", "tag": "backend", "keyword": "历史"},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["related_commit_hash"] == "abcdef1"
    paged = await client.get(
        "/api/worklogs", params={"page": 1, "page_size": 1}
    )
    assert paged.json()["page_size"] == 1
    assert (
        await client.get(
            "/api/worklogs",
            params={"date_from": "2026-08-02", "date_to": "2026-08-01"},
        )
    ).status_code == 422

    updated = await client.put(
        f"/api/worklogs/{worklog_id}",
        json={"duration_minutes": 90, "result": "查询与导出可用"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["duration_minutes"] == 90

    refused = await client.delete(
        f"/api/worklogs/{worklog_id}", headers=headers
    )
    assert refused.status_code == 400
    deleted = await client.delete(
        f"/api/worklogs/{worklog_id}?confirmed=true", headers=headers
    )
    assert deleted.status_code == 204
    assert (await client.get(f"/api/worklogs/{worklog_id}")).status_code == 404
    await client.aclose()


@pytest.mark.anyio
async def test_history_combines_git_and_worklogs_and_exports(tmp_path: Path) -> None:
    client, app, headers, project = await authenticated_client(tmp_path)
    created = await client.post(
        "/api/worklogs",
        json={
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "type": "debug",
            "title": "修复历史筛选",
            "duration_minutes": 30,
            "tags": ["history"],
        },
        headers=headers,
    )
    assert created.status_code == 201
    current = datetime.now(timezone.utc)
    with UnitOfWork(app.state.database) as uow:
        repository = uow.repositories.get_by_root_path(str(project))
        assert repository is not None
        uow.commit_records.create(
            CommitRecord(
                id="record_history_1",
                repository_id=repository.id,
                commit_hash=git(project, "rev-parse", "HEAD"),
                branch="master",
                commit_type="feat",
                subject="feat(web): 保存确认记录",
                body=["保留用户确认后的正文"],
                files=["README.md"],
                insertions=1,
                provider_name="mock",
                model_name="mock-model",
                security_summary={"high": 0, "critical": 0},
                confirmed_by_user=True,
                created_at=current,
                updated_at=current,
            )
        )

    history = await client.get("/api/history")
    assert history.status_code == 200
    kinds = {item["record_type"] for item in history.json()["items"]}
    assert {"git_commit", "commit_record", "worklog"}.issubset(kinds)
    assert history.json()["stats"]["development_minutes"] == 30
    assert all("diff" not in item for item in history.json()["items"])
    assert all("authorization" not in str(item).lower() for item in history.json()["items"])
    commit_record = next(
        item
        for item in history.json()["items"]
        if item["record_type"] == "commit_record"
    )
    assert commit_record["ai_provider"] == "mock"
    assert commit_record["ai_model"] == "mock-model"
    assert commit_record["security_summary"]["high"] == 0
    assert commit_record["body"] == ["保留用户确认后的正文"]

    filtered = await client.get(
        "/api/history", params={"record_type": "worklog", "tag": "history"}
    )
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["title"] == "修复历史筛选"

    for export_format, content_type in [
        ("markdown", "text/markdown"),
        ("json", "application/json"),
        ("csv", "text/csv"),
    ]:
        exported = await client.get(
            "/api/history/export", params={"format": export_format}
        )
        assert exported.status_code == 200
        assert content_type in exported.headers["content-type"]
        assert "修复历史筛选" in exported.content.decode("utf-8-sig")
        assert str(project) not in exported.text
    await client.aclose()


@pytest.mark.anyio
async def test_history_rejects_non_git_repository(tmp_path: Path) -> None:
    project = tmp_path / "plain"
    project.mkdir()
    app = create_app(
        project,
        access_token="fixed-token",
        user_config_path=tmp_path / "user" / "config.yml",
        secrets_path=tmp_path / "user" / "secrets.yml",
        database=Database(tmp_path / "gitpulse.db"),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1:8765",
    ) as client:
        await client.get("/auth/local?token=fixed-token", follow_redirects=False)
        response = await client.get("/api/history")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_a_git_repository"

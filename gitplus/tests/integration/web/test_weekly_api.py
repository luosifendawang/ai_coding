from __future__ import annotations

import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

pytest.importorskip("fastapi")

from gitplus.ai.mock_provider import MockLLMProvider
from gitplus.models.storage import CommitRecord
from gitplus.storage.database import Database
from gitplus.storage.unit_of_work import UnitOfWork
from gitplus.web.app import create_app


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
    (project / "weekly.py").write_text("enabled = True\n", encoding="utf-8")
    git(project, "add", "--", "weekly.py")
    git(project, "commit", "-m", "feat(web): 增加周报管理")
    app = create_app(
        project,
        access_token="fixed-token",
        user_config_path=tmp_path / "user" / "config.yml",
        secrets_path=tmp_path / "user" / "secrets.yml",
        database=Database(tmp_path / "gitplus.db"),
        commit_provider=MockLLMProvider(responses=["not valid json"]),
    )
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1:8765",
    )
    await client.get("/auth/local?token=fixed-token", follow_redirects=False)
    session_id = client.cookies.get("gitplus_session")
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


def range_payload() -> dict[str, object]:
    today = datetime.now(timezone.utc).date().isoformat()
    return {
        "range_kind": "custom",
        "date_from": today,
        "date_to": today,
        "authors": ["test@example.com"],
        "include_uncommitted": False,
    }


def editable_report(report: dict[str, object]) -> dict[str, object]:
    def item(value: dict[str, object]) -> dict[str, object]:
        return {
            "id": value["id"],
            "content": value["content"],
            "title": value.get("title"),
            "description": value.get("description"),
            "result": value.get("result"),
            "confidence": value["confidence"],
            "sources": deepcopy(value["sources"]),
            "confirmed_by_user": value["confirmed_by_user"],
            "notes": value.get("notes", []),
        }

    return {
        "title": report["title"],
        "completed": [
            {
                "id": topic["id"],
                "title": topic["title"],
                "summary": topic.get("summary"),
                "category": topic["category"],
                "items": [item(value) for value in topic["items"]],
                "confidence": topic["confidence"],
                "confirmed_by_user": topic["confirmed_by_user"],
            }
            for topic in report["completed"]
        ],
        "debugging": [item(value) for value in report["debugging"]],
        "testing": [item(value) for value in report["testing"]],
        "risks": [item(value) for value in report["risks"]],
        "next_week": [item(value) for value in report["next_week"]],
    }


@pytest.mark.anyio
async def test_weekly_preview_generate_edit_confirm_reopen_and_export(
    tmp_path: Path,
) -> None:
    client, app, headers, project = await authenticated_client(tmp_path)
    worklog = await client.post(
        "/api/worklogs",
        json={
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "type": "development",
            "title": "完成周报编辑",
            "result": "支持版本控制",
            "duration_minutes": 60,
            "tags": ["weekly"],
        },
        headers=headers,
    )
    assert worklog.status_code == 201
    head = git(project, "rev-parse", "HEAD")
    current = datetime.now(timezone.utc)
    with UnitOfWork(app.state.database) as uow:
        repository = uow.repositories.get_by_root_path(str(project))
        assert repository is not None
        uow.commit_records.create(
            CommitRecord(
                id="record_weekly_1",
                repository_id=repository.id,
                commit_hash=head,
                branch="master",
                commit_type="feat",
                subject="feat(web): 增加周报管理",
                summary="增加周报管理",
                files=["weekly.py"],
                confidence="high",
                confirmed_by_user=True,
                created_at=current,
                updated_at=current,
            )
        )

    assert (
        await client.post("/api/weekly/preview", json=range_payload())
    ).status_code == 403
    preview = await client.post(
        "/api/weekly/preview", json=range_payload(), headers=headers
    )
    assert preview.status_code == 200
    assert preview.json()["counts"]["commits"] == 1
    assert preview.json()["counts"]["commit_records"] == 1
    assert preview.json()["counts"]["worklogs"] == 1
    assert preview.json()["duplicates"]

    generated = await client.post(
        "/api/weekly/generate",
        json={
            **range_payload(),
            "use_ai": True,
            "excluded_source_ids": [],
            "user_context": "",
        },
        headers=headers,
    )
    assert generated.status_code == 201, generated.text
    assert generated.json()["warnings"] == [
        "AI 整理失败，已自动回退到规则模式。"
    ]
    report = generated.json()["report"]
    assert report["status"] == "draft"
    assert report["generator"] == "rule_based"
    report_id = report["id"]

    edited = editable_report(report)
    edited["title"] = "<script>周报</script>"
    edited["debugging"].append(
        {
            "id": "manual_debug_item",
            "content": "补充排查记录",
            "title": "补充排查记录",
            "description": None,
            "result": None,
            "confidence": "high",
            "sources": [],
            "confirmed_by_user": True,
            "notes": [],
        }
    )
    saved = await client.put(
        f"/api/weekly/{report_id}",
        json={"version": report["version"], "report": edited},
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    saved_report = saved.json()
    assert saved_report["version"] == 2
    assert (
        saved_report["debugging"][-1]["sources"][0]["source_type"]
        == "user_note"
    )

    forged = editable_report(saved_report)
    forged["completed"][0]["items"][0]["sources"][0]["source_id"] = "forged"
    invalid_source = await client.put(
        f"/api/weekly/{report_id}",
        json={"version": saved_report["version"], "report": forged},
        headers=headers,
    )
    assert invalid_source.status_code == 422
    assert invalid_source.json()["error"]["code"] == "weekly_source_invalid"

    conflict = await client.put(
        f"/api/weekly/{report_id}",
        json={"version": 1, "report": edited},
        headers=headers,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "weekly_version_conflict"

    medium_edit = editable_report(saved_report)
    medium_edit["completed"][0]["items"][0]["confidence"] = "medium"
    medium_edit["completed"][0]["items"][0]["confirmed_by_user"] = False
    medium_saved = await client.put(
        f"/api/weekly/{report_id}",
        json={
            "version": saved_report["version"],
            "report": medium_edit,
        },
        headers=headers,
    )
    assert medium_saved.status_code == 200
    pending = await client.post(
        f"/api/weekly/{report_id}/confirm",
        json={"version": medium_saved.json()["version"]},
        headers=headers,
    )
    assert pending.status_code == 422
    assert pending.json()["error"]["code"] == "weekly_confirmation_required"
    confirmed_edit = editable_report(medium_saved.json())
    confirmed_edit["completed"][0]["items"][0]["confirmed_by_user"] = True
    ready = await client.put(
        f"/api/weekly/{report_id}",
        json={
            "version": medium_saved.json()["version"],
            "report": confirmed_edit,
        },
        headers=headers,
    )
    assert ready.status_code == 200

    confirmed = await client.post(
        f"/api/weekly/{report_id}/confirm",
        json={"version": ready.json()["version"]},
        headers=headers,
    )
    assert confirmed.status_code == 200, confirmed.text
    confirmed_report = confirmed.json()
    assert confirmed_report["status"] == "confirmed"

    changed = editable_report(confirmed_report)
    changed["title"] = "重新编辑的周报"
    reopened_by_edit = await client.put(
        f"/api/weekly/{report_id}",
        json={
            "version": confirmed_report["version"],
            "report": changed,
        },
        headers=headers,
    )
    assert reopened_by_edit.status_code == 200
    assert reopened_by_edit.json()["status"] == "draft"

    confirmed_again = await client.post(
        f"/api/weekly/{report_id}/confirm",
        json={"version": reopened_by_edit.json()["version"]},
        headers=headers,
    )
    assert confirmed_again.status_code == 200
    confirmed_export = await client.get(
        f"/api/weekly/{report_id}/export",
        params={"format": "markdown"},
    )
    assert confirmed_export.status_code == 200
    exported_report = (
        await client.get(f"/api/weekly/{report_id}")
    ).json()
    assert exported_report["status"] == "exported"
    reopened = await client.post(
        f"/api/weekly/{report_id}/reopen",
        json={"version": exported_report["version"]},
        headers=headers,
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "draft"

    for export_format, content_type in [
        ("markdown", "text/markdown"),
        ("text", "text/plain"),
        ("json", "application/json"),
    ]:
        exported = await client.get(
            f"/api/weekly/{report_id}/export",
            params={"format": export_format},
        )
        assert exported.status_code == 200
        assert content_type in exported.headers["content-type"]
        assert "重新编辑的周报" in exported.text
        assert str(project) not in exported.text

    page = await client.get(f"/weekly/{report_id}")
    assert page.status_code == 200
    assert "weekly-detail.js" in page.text
    assert "textContent" in (
        Path("src/gitplus/web/static/js/weekly-detail.js")
        .read_text(encoding="utf-8")
    )
    await client.aclose()


@pytest.mark.anyio
async def test_weekly_empty_period_and_delete_confirmation(
    tmp_path: Path,
) -> None:
    client, _app, headers, _project = await authenticated_client(tmp_path)
    empty = {
        "range_kind": "custom",
        "date_from": "2000-01-01",
        "date_to": "2000-01-01",
        "authors": ["test@example.com"],
        "include_uncommitted": False,
    }
    preview = await client.post(
        "/api/weekly/preview", json=empty, headers=headers
    )
    assert preview.status_code == 200
    assert preview.json()["counts"]["usable"] == 0
    generated = await client.post(
        "/api/weekly/generate",
        json={**empty, "use_ai": False},
        headers=headers,
    )
    assert generated.status_code == 422

    report_response = await client.post(
        "/api/weekly/generate",
        json={**range_payload(), "use_ai": False},
        headers=headers,
    )
    assert report_response.status_code == 201
    report = report_response.json()["report"]
    refused = await client.delete(
        f"/api/weekly/{report['id']}",
        params={"version": report["version"]},
        headers=headers,
    )
    assert refused.status_code == 400
    deleted = await client.delete(
        f"/api/weekly/{report['id']}",
        params={"version": report["version"], "confirmed": "true"},
        headers=headers,
    )
    assert deleted.status_code == 204
    await client.aclose()

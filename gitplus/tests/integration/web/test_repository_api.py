from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
import httpx

from gitplus.ai.mock_provider import MockLLMProvider
from gitplus.storage.database import Database
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
    (project / "README.md").write_text("start\n", encoding="utf-8")
    git(project, "add", "--", "README.md")
    git(project, "commit", "-m", "chore: initialize")
    app = create_app(
        project,
        access_token="fixed-token",
        user_config_path=tmp_path / "user" / "config.yml",
        secrets_path=tmp_path / "user" / "secrets.yml",
        database=Database(tmp_path / "gitplus.db"),
        commit_provider=MockLLMProvider(),
    )
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1:8765",
    )
    await client.get("/auth/local?token=fixed-token", follow_redirects=False)
    session_id = client.cookies.get("gitplus_session")
    csrf = app.state.sessions.get(session_id).csrf_token
    headers = {
        "origin": "http://127.0.0.1:8765",
        "x-csrf-token": csrf,
    }
    return client, app, headers, project


@pytest.mark.anyio
async def test_repository_full_commit_api_flow(tmp_path: Path) -> None:
    client, _app, headers, project = await authenticated_client(tmp_path)
    (project / "feature.py").write_text("enabled = True\n", encoding="utf-8")

    status = (await client.get("/api/repository/status")).json()
    assert status["summary"]["untracked"] == 1

    diff = await client.get(
        "/api/repository/diff",
        params={"path": "feature.py", "source": "unstaged"},
    )
    assert diff.status_code == 200
    assert "+enabled = True" in diff.json()["diff"]

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
            "context": "新增功能开关",
            "scan_id": scan.json()["scan_id"],
            "revision": revision,
        },
        headers=headers,
    )
    assert generated.status_code == 200
    assert len(generated.json()["candidates"]) == 3

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
    assert committed.json()["success"] is True
    assert git(project, "log", "-1", "--pretty=%s") == "feat(core): 增加功能开关"
    await client.aclose()


@pytest.mark.anyio
async def test_repository_write_requires_csrf_and_current_revision(
    tmp_path: Path,
) -> None:
    client, _app, headers, project = await authenticated_client(tmp_path)
    (project / "feature.py").write_text("enabled = True\n", encoding="utf-8")
    status = (await client.get("/api/repository/status")).json()

    unauthorized = await client.post(
        "/api/repository/stage",
        json={"paths": ["feature.py"], "revision": status["revision"]},
    )
    assert unauthorized.status_code == 403
    (project / "other.py").write_text("changed = True\n", encoding="utf-8")
    conflict = await client.post(
        "/api/repository/stage",
        json={"paths": ["feature.py"], "revision": status["revision"]},
        headers=headers,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "repository_changed"
    await client.aclose()


@pytest.mark.anyio
async def test_repository_path_escape_is_rejected(tmp_path: Path) -> None:
    client, _app, headers, project = await authenticated_client(tmp_path)
    (project / "feature.py").write_text("enabled = True\n", encoding="utf-8")
    status = (await client.get("/api/repository/status")).json()

    response = await client.post(
        "/api/repository/stage",
        json={"paths": ["../outside"], "revision": status["revision"]},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "path_outside_repository"
    await client.aclose()

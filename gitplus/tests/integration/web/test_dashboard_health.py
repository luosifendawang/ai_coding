from __future__ import annotations

import subprocess
from pathlib import Path

import httpx
import pytest

pytest.importorskip("fastapi")

from gitplus.storage.database import Database
from gitplus.web.app import create_app


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


async def authenticated_client(
    tmp_path: Path,
) -> tuple[httpx.AsyncClient, object, dict[str, str]]:
    project = tmp_path / "repo"
    project.mkdir()
    git(project, "init")
    git(project, "config", "user.name", "Test User")
    git(project, "config", "user.email", "test@example.com")
    (project / "app.py").write_text("print('hello')\n", encoding="utf-8")
    git(project, "add", "--", "app.py")
    git(project, "commit", "-m", "feat: init")
    (project / "app.py").write_text("print('hello dashboard')\n", encoding="utf-8")
    app = create_app(
        project,
        access_token="fixed-token",
        user_config_path=tmp_path / "user" / "config.yml",
        secrets_path=tmp_path / "user" / "secrets.yml",
        database=Database(tmp_path / "gitplus.db"),
    )
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1:8765",
    )
    await client.get("/auth/local?token=fixed-token", follow_redirects=False)
    session_id = client.cookies.get("gitplus_session")
    csrf = app.state.sessions.get(session_id).csrf_token
    return client, app, {"origin": "http://127.0.0.1:8765", "x-csrf-token": csrf}


@pytest.mark.anyio
async def test_dashboard_and_health_details(tmp_path: Path) -> None:
    client, app, _headers = await authenticated_client(tmp_path)
    try:
        health = await client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["web"] == "running"

        dashboard = await client.get("/api/dashboard")
        assert dashboard.status_code == 200
        body = dashboard.json()
        assert body["repository"]["branch"] in {"master", "main"}
        assert body["git_summary"]["unstaged"] == 1
        assert body["database"]["schema_version"]
        assert "app_secret" not in dashboard.text

        details_without_session = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://127.0.0.1:8765",
        )
        try:
            assert (await details_without_session.get("/api/health/details")).status_code == 403
        finally:
            await details_without_session.aclose()

        details = await client.get("/api/health/details")
        assert details.status_code == 200
        assert details.json()["database"]["expected_schema_version"]

        index = await client.get("/")
        assert index.status_code == 200
        assert "本周 Commit" in index.text
        assert "dashboard.js" in index.text
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_html_errors_do_not_show_tracebacks(tmp_path: Path) -> None:
    client, _app, _headers = await authenticated_client(tmp_path)
    try:
        missing = await client.get("/does-not-exist")
        assert missing.status_code == 404
        assert "Traceback" not in missing.text
        assert "返回仪表盘" in missing.text
    finally:
        await client.aclose()

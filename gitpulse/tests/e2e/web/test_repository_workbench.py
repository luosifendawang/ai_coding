from __future__ import annotations

import subprocess
from pathlib import Path

import httpx
import pytest

pytest.importorskip("fastapi")

from gitpulse.web.app import create_app


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.anyio
async def test_repository_workbench_renders_fixed_repository(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    git(project, "init")
    git(project, "config", "user.name", "Test User")
    git(project, "config", "user.email", "test@example.com")
    (project / "README.md").write_text("start\n", encoding="utf-8")
    git(project, "add", "--", "README.md")
    git(project, "commit", "-m", "chore: initialize")
    (project / "feature.py").write_text("enabled = True\n", encoding="utf-8")
    app = create_app(
        project,
        access_token="fixed-token",
        user_config_path=tmp_path / "user" / "config.yml",
        secrets_path=tmp_path / "user" / "secrets.yml",
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1:8765",
    ) as client:
        await client.get("/auth/local?token=fixed-token", follow_redirects=False)
        page = await client.get("/repository")
        status = await client.get("/api/repository/status")

    assert page.status_code == 200
    assert "Git 工作台" in page.text
    assert "Commit 助手" in page.text
    assert "repository.js" in page.text
    assert status.json()["repository"]["root"] == str(project)
    assert status.json()["files"][0]["path"] == "feature.py"

from pathlib import Path

import httpx
import pytest

pytest.importorskip("fastapi")

from gitplus.storage.database import Database
from gitplus.web.app import create_app


@pytest.mark.anyio
async def test_worklog_and_history_pages_are_protected_and_render(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    app = create_app(
        project,
        access_token="fixed-token",
        user_config_path=tmp_path / "user" / "config.yml",
        secrets_path=tmp_path / "user" / "secrets.yml",
        database=Database(tmp_path / "gitplus.db"),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1:8765",
    ) as client:
        assert (await client.get("/worklogs")).status_code == 403
        await client.get("/auth/local?token=fixed-token", follow_redirects=False)
        worklogs = await client.get("/worklogs")
        history = await client.get("/history")

    assert worklogs.status_code == 200
    assert "新增日志" in worklogs.text
    assert "worklogs.js" in worklogs.text
    assert history.status_code == 200
    assert "Git Commit" in history.text
    assert "history.js" in history.text

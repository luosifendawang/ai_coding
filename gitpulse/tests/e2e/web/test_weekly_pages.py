from pathlib import Path

import httpx
import pytest

pytest.importorskip("fastapi")

from gitpulse.storage.database import Database
from gitpulse.web.app import create_app


@pytest.mark.anyio
async def test_weekly_pages_require_session_and_render(tmp_path: Path) -> None:
    project = tmp_path / "project"
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
        assert (await client.get("/weekly")).status_code == 403
        await client.get("/auth/local?token=fixed-token", follow_redirects=False)
        index = await client.get("/weekly")
        detail = await client.get("/weekly/example")

    assert index.status_code == 200
    assert "预览数据" in index.text
    assert "weekly.js" in index.text
    assert detail.status_code == 200
    assert "来源追踪" in detail.text

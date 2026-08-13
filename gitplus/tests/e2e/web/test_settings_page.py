from pathlib import Path

import pytest

pytest.importorskip("fastapi")
import httpx

from gitplus.web.app import create_app


@pytest.mark.anyio
async def test_settings_page_contains_system_config_workflow(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
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
        response = await client.get("/settings")

        assert response.status_code == 200
        for label in [
            "常规设置",
            "AI 设置",
            "安全设置",
            "Git 设置",
            "存储设置",
            "周报设置",
            "飞书设置",
            "Web 设置",
            "配置来源",
        ]:
            assert label in response.text
        assert "预览并保存" in response.text
        assert "settings.js" in response.text
        assert "never-return-this" not in response.text

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
import httpx

from gitpulse.web.app import create_app


def make_client(tmp_path: Path) -> tuple[httpx.AsyncClient, object]:
    project = tmp_path / "project"
    project.mkdir()
    app = create_app(
        project,
        access_token="fixed-token",
        user_config_path=tmp_path / "user" / "config.yml",
        secrets_path=tmp_path / "user" / "secrets.yml",
    )
    return (
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://127.0.0.1:8765",
        ),
        app,
    )


async def authenticate(client: httpx.AsyncClient, app) -> str:
    response = await client.get("/auth/local?token=fixed-token", follow_redirects=False)
    assert response.status_code == 303
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    session_id = client.cookies.get("gitpulse_session")
    return app.state.sessions.get(session_id).csrf_token


@pytest.mark.anyio
async def test_local_auth_and_protected_pages(tmp_path: Path) -> None:
    client, app = make_client(tmp_path)
    async with client:
        assert (await client.get("/api/config/effective")).status_code == 403
        csrf = await authenticate(client, app)
        assert csrf
        assert (await client.get("/")).status_code == 200
        settings = await client.get("/settings")
        assert settings.status_code == 200
        assert "系统配置" in settings.text


@pytest.mark.anyio
async def test_invalid_token_host_origin_and_csrf_are_rejected(
    tmp_path: Path,
) -> None:
    client, app = make_client(tmp_path)
    async with client:
        assert (
            await client.get("/auth/local?token=wrong", follow_redirects=False)
        ).status_code == 403
        csrf = await authenticate(client, app)
        assert (
            await client.get("/api/config/effective", headers={"host": "example.com"})
        ).status_code == 403

        payload = {"scope": "project", "config": {}}
        assert (
            await client.post("/api/config/validate", json=payload)
        ).status_code == 403
        assert (
            await client.post(
                "/api/config/validate",
                json=payload,
                headers={"origin": "http://example.com", "x-csrf-token": csrf},
            )
        ).status_code == 403
        assert (
            await client.post(
                "/api/config/validate",
                json=payload,
                headers={
                    "origin": "http://127.0.0.1:8765",
                    "x-csrf-token": "wrong",
                },
            )
        ).status_code == 403

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
import httpx

from gitpulse.web.app import create_app


async def authenticated_client(
    tmp_path: Path,
) -> tuple[httpx.AsyncClient, object, dict[str, str]]:
    project = tmp_path / "project"
    project.mkdir()
    app = create_app(
        project,
        access_token="fixed-token",
        user_config_path=tmp_path / "user" / "config.yml",
        secrets_path=tmp_path / "user" / "secrets.yml",
    )
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1:8765",
    )
    await client.get("/auth/local?token=fixed-token", follow_redirects=False)
    session_id = client.cookies.get("gitpulse_session")
    csrf = app.state.sessions.get(session_id).csrf_token
    headers = {"origin": "http://127.0.0.1:8765", "x-csrf-token": csrf}
    return client, app, headers


@pytest.mark.anyio
async def test_effective_config_never_returns_secret(tmp_path: Path) -> None:
    client, app, _headers = await authenticated_client(tmp_path)
    app.state.config_service.paths.secrets.parent.mkdir(parents=True)
    app.state.config_service.paths.secrets.write_text(
        "ai:\n  api_key: never-return-this\n",
        encoding="utf-8",
    )

    response = await client.get("/api/config/effective")

    assert response.status_code == 200
    assert "never-return-this" not in response.text
    assert response.json()["secrets"]["ai.api_key"]["configured"] is True
    await client.aclose()


@pytest.mark.anyio
async def test_validate_preview_save_and_revision_conflict(tmp_path: Path) -> None:
    client, _app, headers = await authenticated_client(tmp_path)
    effective = (await client.get("/api/config/effective")).json()
    payload = {
        "scope": "project",
        "config": {"ai": {"model": "web-model"}},
        "secret_updates": {
            "ai.api_key": {"action": "replace", "value": "secret-value-123"}
        },
        "revision": effective["revision"],
    }

    validation = await client.post(
        "/api/config/validate", json=payload, headers=headers
    )
    assert validation.status_code == 200
    assert validation.json()["valid"] is True

    preview = await client.post("/api/config/preview", json=payload, headers=headers)
    assert preview.status_code == 200
    assert "secret-value-123" not in preview.text
    assert any(item["path"] == "ai.model" for item in preview.json()["changes"])

    payload["confirmed"] = True
    saved = await client.put("/api/config", json=payload, headers=headers)
    assert saved.status_code == 200
    assert saved.json()["config"]["ai"]["model"] == "web-model"
    assert "secret-value-123" not in saved.text

    conflict = await client.put("/api/config", json=payload, headers=headers)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "config_changed"
    await client.aclose()


@pytest.mark.anyio
async def test_invalid_config_returns_field_errors(tmp_path: Path) -> None:
    client, _app, headers = await authenticated_client(tmp_path)

    response = await client.post(
        "/api/config/validate",
        json={"scope": "project", "config": {"ai": {"timeout_seconds": 0}}},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert body["errors"][0]["path"] == "ai.timeout_seconds"
    await client.aclose()

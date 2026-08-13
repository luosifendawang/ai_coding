import stat
from pathlib import Path

import pytest
import yaml

from gitplus.web.schemas.config import ConfigUpdateRequest, SecretUpdate
from gitplus.web.services.config_web_service import (
    ConfigConflictError,
    ConfigWebService,
)


def service(tmp_path: Path) -> ConfigWebService:
    project = tmp_path / "project"
    project.mkdir()
    return ConfigWebService(
        project,
        user_path=tmp_path / "config" / "config.yml",
        secrets_path=tmp_path / "config" / "secrets.yml",
    )


def test_effective_config_tracks_sources_and_hides_secrets(tmp_path: Path) -> None:
    current = service(tmp_path)
    current.paths.user_config.parent.mkdir(parents=True)
    current.paths.user_config.write_text("ai:\n  model: user-model\n", encoding="utf-8")
    current.paths.project_config.write_text(
        "ai:\n  model: project-model\n", encoding="utf-8"
    )
    current.paths.secrets.write_text(
        "ai:\n  api_key: never-return-this\n", encoding="utf-8"
    )

    result = current.get_effective_config()

    assert result["config"]["ai"]["model"] == "project-model"
    assert "api_key" not in result["config"]["ai"]
    assert result["sources"]["ai.model"] == "project"
    assert result["secrets"]["ai.api_key"] == {
        "configured": True,
        "source": "user_secret",
    }
    assert "never-return-this" not in str(result)


def test_effective_config_reports_environment_secret_without_value(
    tmp_path: Path, monkeypatch
) -> None:
    current = service(tmp_path)
    monkeypatch.setenv("GITPLUS_API_KEY", "environment-secret-value")

    result = current.get_effective_config()

    assert result["secrets"]["ai.api_key"] == {
        "configured": True,
        "source": "environment",
    }
    assert "environment-secret-value" not in str(result)


def test_save_is_minimal_atomic_and_preserves_unknown_fields(tmp_path: Path) -> None:
    current = service(tmp_path)
    current.paths.project_config.write_text(
        "plugin_future:\n  enabled: true\nai:\n  model: old-model\n",
        encoding="utf-8",
    )
    request = ConfigUpdateRequest(
        scope="project",
        config={"ai": {"model": "new-model"}},
        revision=current.revision(),
        confirmed=True,
    )

    result = current.save_update(request)
    stored = yaml.safe_load(current.paths.project_config.read_text(encoding="utf-8"))

    assert stored["plugin_future"]["enabled"] is True
    assert stored["ai"] == {"model": "new-model"}
    assert result["config"]["ai"]["model"] == "new-model"
    assert list(current.paths.project_config.parent.glob(".gitplus.yml.bak.*"))


def test_secret_replace_keep_delete_and_permissions(tmp_path: Path) -> None:
    current = service(tmp_path)
    replace = ConfigUpdateRequest(
        scope="user",
        secret_updates={
            "ai.api_key": SecretUpdate(action="replace", value="secret-value-123")
        },
        revision=current.revision(),
        confirmed=True,
    )
    current.save_update(replace)

    assert current.secret_value("ai.api_key") == "secret-value-123"
    assert stat.S_IMODE(current.paths.secrets.stat().st_mode) == 0o600
    assert "secret-value-123" not in str(current.get_effective_config())

    keep = ConfigUpdateRequest(
        scope="user",
        secret_updates={"ai.api_key": SecretUpdate(action="keep")},
        revision=current.revision(),
        confirmed=True,
    )
    current.save_update(keep)
    assert current.secret_value("ai.api_key") == "secret-value-123"

    delete = ConfigUpdateRequest(
        scope="user",
        secret_updates={"ai.api_key": SecretUpdate(action="delete")},
        revision=current.revision(),
        confirmed=True,
    )
    current.save_update(delete)
    assert current.secret_value("ai.api_key") is None


def test_revision_conflict_does_not_overwrite_external_change(tmp_path: Path) -> None:
    current = service(tmp_path)
    revision = current.revision()
    current.paths.project_config.write_text(
        "ai:\n  model: external\n", encoding="utf-8"
    )

    with pytest.raises(ConfigConflictError):
        current.save_update(
            ConfigUpdateRequest(
                scope="project",
                config={"ai": {"model": "browser"}},
                revision=revision,
                confirmed=True,
            )
        )

    assert "external" in current.paths.project_config.read_text(encoding="utf-8")


def test_preview_masks_secret_and_reports_restart(tmp_path: Path) -> None:
    current = service(tmp_path)
    result = current.preview_update(
        ConfigUpdateRequest(
            scope="project",
            config={"web": {"port": 8899}},
            secret_updates={
                "ai.api_key": SecretUpdate(action="replace", value="secret-value-123")
            },
            revision=current.revision(),
        )
    )

    assert result["valid"] is True
    assert result["restart_required"] == ["web.port"]
    assert "secret-value-123" not in str(result)
    assert any(change["path"] == "ai.api_key" for change in result["changes"])

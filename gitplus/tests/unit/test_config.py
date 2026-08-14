from pathlib import Path

import pytest
from pydantic import ValidationError

import gitplus.config as config_module
from gitplus.config import (
    GitPlusConfig,
    default_config,
    load_config,
    user_config_path,
    user_secrets_path,
)


def test_default_config_contains_safe_secret_env_names() -> None:
    config = default_config()

    assert config.ai.api_key_env == "GITPLUS_API_KEY"
    assert config.feishu.app_id_env == "GITPLUS_FEISHU_APP_ID"
    assert config.feishu.app_secret_env == "GITPLUS_FEISHU_APP_SECRET"
    assert config.feishu.receive_id_env == "GITPLUS_FEISHU_RECEIVE_ID"


def test_global_config_and_secrets_are_stored_beside_database() -> None:
    root = Path("~/.gitplus/.config").expanduser()

    assert user_config_path() == root / "config.yml"
    assert user_secrets_path() == root / "secrets.yml"


def test_invalid_commit_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        GitPlusConfig(commit={"allowed_types": ["feat", "invalid"]})


def test_load_config_ignores_project_gitplus_yml(tmp_path, monkeypatch) -> None:
    (tmp_path / ".gitplus.yml").write_text(
        """
ai:
  provider: openai-compatible
  base_url: https://api.example.test/v1
  model: configured-model
  api_key: configured-key
  api_key_env: EXAMPLE_API_KEY
  is_local: false
commit:
  language: en-US
""",
        encoding="utf-8",
    )

    global_config = tmp_path / "global" / "config.yml"
    monkeypatch.setattr(config_module, "user_config_path", lambda: global_config)
    monkeypatch.setattr(config_module, "user_secrets_path", lambda: tmp_path / "global" / "secrets.yml")

    config = load_config()

    assert config.ai.model == default_config().ai.model
    assert config.ai.api_key is None
    assert config.commit.language == default_config().commit.language
    assert config.diff.max_total_chars == default_config().diff.max_total_chars


def test_load_config_reads_global_user_config(tmp_path, monkeypatch) -> None:
    path = tmp_path / "global" / "config.yml"
    path.parent.mkdir()
    path.write_text("ai:\n  model: global-model\n", encoding="utf-8")
    monkeypatch.setattr(config_module, "user_config_path", lambda: path)
    monkeypatch.setattr(config_module, "user_secrets_path", lambda: tmp_path / "global" / "secrets.yml")

    assert load_config().ai.model == "global-model"

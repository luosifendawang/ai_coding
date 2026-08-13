import pytest
from pydantic import ValidationError

from gitplus.config import GitPlusConfig, default_config, load_config


def test_default_config_contains_safe_secret_env_names() -> None:
    config = default_config()

    assert config.ai.api_key_env == "GITPLUS_API_KEY"
    assert config.feishu.app_id_env == "GITPLUS_FEISHU_APP_ID"
    assert config.feishu.app_secret_env == "GITPLUS_FEISHU_APP_SECRET"
    assert config.feishu.receive_id_env == "GITPLUS_FEISHU_RECEIVE_ID"


def test_invalid_commit_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        GitPlusConfig(commit={"allowed_types": ["feat", "invalid"]})


def test_load_config_reads_project_gitplus_yml(tmp_path) -> None:
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

    config = load_config(tmp_path)

    assert config.ai.model == "configured-model"
    assert config.ai.base_url == "https://api.example.test/v1"
    assert config.ai.api_key == "configured-key"
    assert config.ai.api_key_env == "EXAMPLE_API_KEY"
    assert config.ai.is_local is False
    assert config.commit.language == "en-US"
    assert config.diff.max_total_chars == default_config().diff.max_total_chars

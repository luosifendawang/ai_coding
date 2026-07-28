from pathlib import Path

import yaml

from gitpulse.config import default_config
from gitpulse.setup.config_writer import ConfigWriter


def test_config_writer_does_not_write_secret_values_and_preserves_unknown(tmp_path: Path) -> None:
    path = tmp_path / "config.yml"
    path.write_text("custom:\n  kept: true\n", encoding="utf-8")

    ConfigWriter().write(path, default_config())
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert data["custom"]["kept"] is True
    assert "webhook" not in data["feishu"]
    assert "secret" not in data["feishu"]
    assert data["ai"]["api_key_env"] == "GITPULSE_API_KEY"
    assert list(tmp_path.glob("config.yml.bak.*"))

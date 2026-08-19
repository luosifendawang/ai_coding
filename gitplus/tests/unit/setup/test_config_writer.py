from pathlib import Path

import yaml

from gitplus.config import default_config
from gitplus.setup.config_writer import ConfigWriter


def test_config_writer_does_not_write_secret_values_and_preserves_unknown(
    tmp_path: Path,
) -> None:
    path = tmp_path / "config.yml"
    path.write_text("custom:\n  kept: true\n", encoding="utf-8")

    ConfigWriter().write(path, default_config())
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert data["custom"]["kept"] is True
    assert data["ai"]["api_key_env"] == "GITPLUS_API_KEY"
    assert list(tmp_path.glob("config.yml.bak.*"))

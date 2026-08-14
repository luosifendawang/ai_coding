"""Setup environment paths."""

from __future__ import annotations

from pathlib import Path


def user_config_path() -> Path:
    return Path("~/.gitplus/.config/config.yml").expanduser()

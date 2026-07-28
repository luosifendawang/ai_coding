"""Setup environment paths."""

from __future__ import annotations

import os
from pathlib import Path


def user_config_path() -> Path:
    base = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "gitpulse" / "config.yml"


def project_config_path(cwd: Path | None = None) -> Path:
    return (cwd or Path.cwd()) / ".gitpulse.yml"

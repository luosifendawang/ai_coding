"""Setup input validators."""

from __future__ import annotations

from pathlib import Path

from gitplus.exceptions import ConfigurationError


class SetupValidator:
    """Validate setup output paths and values."""

    def validate_output_path(self, path: Path, *, project: bool = False) -> None:
        resolved = path.expanduser().resolve()
        if project or resolved.name != "config.yml":
            raise ConfigurationError("全局配置文件必须命名为 config.yml。")

"""Setup input validators."""

from __future__ import annotations

from pathlib import Path

from gitpulse.exceptions import ConfigurationError


class SetupValidator:
    """Validate setup output paths and values."""

    def validate_output_path(self, path: Path, *, project: bool) -> None:
        resolved = path.expanduser().resolve()
        if project:
            cwd = Path.cwd().resolve()
            if resolved.parent != cwd:
                raise ConfigurationError("项目级配置只能写入当前目录的 .gitpulse.yml。")
        if resolved.name not in {"config.yml", ".gitpulse.yml"}:
            raise ConfigurationError("配置文件名不符合预期。")

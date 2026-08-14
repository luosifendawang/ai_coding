"""Non-secret setup wizard."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gitplus.config import GitPlusConfig, default_config, user_config_path
from gitplus.setup.config_writer import ConfigWriter
from gitplus.setup.validators import SetupValidator


@dataclass(frozen=True)
class SetupResult:
    path: Path
    preview: str
    written: bool


class SetupWizard:
    """Prepare and optionally write gitplus config."""

    def __init__(
        self,
        *,
        config: GitPlusConfig | None = None,
        writer: ConfigWriter | None = None,
        validator: SetupValidator | None = None,
    ) -> None:
        self.config = config or default_config()
        self.writer = writer or ConfigWriter()
        self.validator = validator or SetupValidator()

    def run(self, *, write: bool) -> SetupResult:
        """Create or preview the one global user configuration file."""
        path = user_config_path()
        self.validator.validate_output_path(path, project=False)
        preview = self.writer.preview(self.config)
        if write:
            self.writer.write(path, self.config)
        return SetupResult(path=path, preview=preview, written=write)

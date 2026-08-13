"""Configuration backup and atomic file helpers."""

from __future__ import annotations

import os
import shutil
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path


class ConfigBackupService:
    """Create, restore, and prune timestamped configuration backups."""

    def create_backup(self, path: Path, *, secret: bool = False) -> Path | None:
        if not path.exists():
            return None
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        backup = path.with_name(f"{path.name}.bak.{stamp}")
        shutil.copy2(path, backup)
        if secret:
            backup.chmod(stat.S_IRUSR | stat.S_IWUSR)
        return backup

    def restore_backup(
        self, backup_path: Path, target_path: Path, *, secret: bool = False
    ) -> None:
        self.atomic_write(target_path, backup_path.read_bytes(), secret=secret)

    def cleanup_old_backups(self, path: Path, keep: int) -> None:
        backups = sorted(
            path.parent.glob(f"{path.name}.bak.*"),
            key=lambda item: item.stat().st_mtime_ns,
            reverse=True,
        )
        for stale in backups[keep:]:
            stale.unlink(missing_ok=True)

    def latest_backup(self, path: Path) -> Path | None:
        backups = sorted(
            path.parent.glob(f"{path.name}.bak.*"),
            key=lambda item: item.stat().st_mtime_ns,
            reverse=True,
        )
        return backups[0] if backups else None

    def atomic_write(self, path: Path, content: bytes, *, secret: bool = False) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temp_path = Path(temp_name)
        try:
            mode = stat.S_IRUSR | stat.S_IWUSR
            os.fchmod(descriptor, mode)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
            if secret:
                path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        finally:
            temp_path.unlink(missing_ok=True)

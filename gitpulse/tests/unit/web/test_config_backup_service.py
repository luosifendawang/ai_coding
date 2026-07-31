import stat
from pathlib import Path

from gitpulse.web.services.config_backup_service import ConfigBackupService


def test_backup_restore_cleanup_and_secret_mode(tmp_path: Path) -> None:
    service = ConfigBackupService()
    target = tmp_path / "secrets.yml"
    target.write_text("first", encoding="utf-8")
    backup = service.create_backup(target, secret=True)
    assert backup is not None
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600

    service.atomic_write(target, b"second", secret=True)
    service.restore_backup(backup, target, secret=True)
    assert target.read_text(encoding="utf-8") == "first"

    service.cleanup_old_backups(target, keep=0)
    assert not backup.exists()

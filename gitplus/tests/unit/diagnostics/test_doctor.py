from pathlib import Path

from gitplus.config import default_config
from gitplus.diagnostics.doctor import DoctorService
from gitplus.diagnostics.models import DiagnosticStatus
from gitplus.storage.database import Database


def test_doctor_runs_with_temp_database(tmp_path: Path) -> None:
    config = default_config()
    config.storage.database = tmp_path / "doctor.db"

    report = DoctorService(config, database=Database(config.storage.database_path)).run()

    ids = {item.id for item in report.items}
    assert "python" in ids
    assert "database" in ids
    assert report.status in {DiagnosticStatus.PASS, DiagnosticStatus.WARNING}

from pathlib import Path

from sqlalchemy import select

from gitpulse.storage.database import Database
from gitpulse.storage.orm_models import OperationAuditORM
from gitpulse.web.services.operation_audit_service import OperationAuditService


def test_operation_audit_persists_only_safe_metadata(tmp_path: Path) -> None:
    database = Database(tmp_path / "gitpulse.db")
    service = OperationAuditService(database)

    service.record(
        "files_staged",
        repository="/private/project",
        success=True,
        file_count=2,
        session_id="secret-session-token",
    )

    with database.session_scope() as session:
        saved = session.execute(select(OperationAuditORM)).scalar_one()
    assert saved.operation == "files_staged"
    assert saved.file_count == 2
    assert saved.repository_hash != "/private/project"
    assert saved.session_hash != "secret-session-token"
    assert "secret-session-token" not in str(service.entries())
    database.dispose()

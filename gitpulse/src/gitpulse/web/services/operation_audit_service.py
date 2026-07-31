"""Minimal local operation audit without sensitive payloads."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from hashlib import sha256
from threading import Lock
from uuid import uuid4

from loguru import logger

from gitpulse.storage.database import Database
from gitpulse.storage.orm_models import OperationAuditORM


class OperationAuditService:
    def __init__(
        self, database: Database | None = None, max_entries: int = 500
    ) -> None:
        self.database = database
        self._entries: deque[dict[str, object]] = deque(maxlen=max_entries)
        self._lock = Lock()

    def record(
        self,
        operation: str,
        *,
        repository: str,
        success: bool,
        file_count: int = 0,
        error_code: str | None = None,
        session_id: str | None = None,
    ) -> None:
        entry = {
            "operation": operation,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "repository": sha256(repository.encode("utf-8")).hexdigest()[:12],
            "success": success,
            "file_count": file_count,
            "error_code": error_code,
            "session": (
                sha256(session_id.encode("utf-8")).hexdigest()[:12]
                if session_id
                else None
            ),
        }
        with self._lock:
            self._entries.append(entry)
        if self.database is not None:
            try:
                self.database.initialize()
                with self.database.session_scope() as session:
                    session.add(
                        OperationAuditORM(
                            id=f"audit_{uuid4().hex[:16]}",
                            operation=operation,
                            repository_hash=str(entry["repository"]),
                            success=success,
                            file_count=file_count,
                            error_code=error_code,
                            session_hash=(
                                str(entry["session"]) if entry["session"] else None
                            ),
                        )
                    )
            except Exception as exc:  # noqa: BLE001 - audit must not break Git operations
                logger.warning(
                    "web_git_audit_persist_failed error_type={}",
                    type(exc).__name__,
                )
        logger.info(
            "web_git_operation operation={} success={} file_count={} error_code={}",
            operation,
            success,
            file_count,
            error_code or "",
        )

    def entries(self) -> list[dict[str, object]]:
        with self._lock:
            return list(self._entries)

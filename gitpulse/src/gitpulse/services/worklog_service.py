"""Worklog business service."""

from __future__ import annotations

from datetime import date, datetime, timezone

from gitpulse.exceptions import RecordNotFoundError, SensitiveContentError
from gitpulse.models.diff import DiffCollection, DiffSource, FileChangeStatus, FileDiff
from gitpulse.models.worklog import Worklog, WorklogCreate, WorklogFilters, WorklogUpdate
from gitpulse.services.security_service import SecurityService
from gitpulse.storage.database import Database
from gitpulse.storage.serializers import IdGenerator
from gitpulse.storage.unit_of_work import UnitOfWork


class WorklogService:
    """Create, update, delete, and query manual worklogs."""

    def __init__(
        self,
        database: Database,
        id_generator: IdGenerator | None = None,
        security_service: SecurityService | None = None,
    ) -> None:
        self.database = database
        self.id_generator = id_generator or IdGenerator()
        self.security_service = security_service or SecurityService()

    def create(self, request: WorklogCreate) -> Worklog:
        self._check_sensitive_text(request)
        current = datetime.now(timezone.utc)
        worklog = Worklog(
            id=self.id_generator.new_worklog_id(),
            repository_id=request.repository_id,
            work_date=request.work_date,
            work_type=request.work_type,
            title=request.title,
            description=request.description,
            result=request.result,
            duration_minutes=request.duration_minutes,
            tags=request.tags,
            created_at=current,
            updated_at=current,
        )
        with UnitOfWork(self.database) as uow:
            return uow.worklogs.create(worklog)

    def get(self, worklog_id: str) -> Worklog:
        with UnitOfWork(self.database) as uow:
            worklog = uow.worklogs.get_by_id(worklog_id)
            if not worklog:
                raise RecordNotFoundError(f"未找到 Worklog：{worklog_id}")
            return worklog

    def update(self, worklog_id: str, request: WorklogUpdate) -> Worklog:
        text = "\n".join(str(getattr(request, field) or "") for field in request.model_fields_set)
        self._check_text(text)
        with UnitOfWork(self.database) as uow:
            return uow.worklogs.update(worklog_id, request)

    def delete(self, worklog_id: str) -> None:
        with UnitOfWork(self.database) as uow:
            if not uow.worklogs.delete(worklog_id):
                raise RecordNotFoundError(f"未找到 Worklog：{worklog_id}")

    def list(self, filters: WorklogFilters) -> list[Worklog]:
        with UnitOfWork(self.database) as uow:
            return uow.worklogs.list(filters)

    def _check_sensitive_text(self, request: WorklogCreate) -> None:
        text = "\n".join(
            value or ""
            for value in [request.title, request.description, request.result, " ".join(request.tags)]
        )
        self._check_text(text)

    def _check_text(self, text: str) -> None:
        collection = DiffCollection(
            source=DiffSource.STAGED,
            files=[
                FileDiff.with_extension(
                    new_path="worklog.txt",
                    status=FileChangeStatus.MODIFIED,
                    patch=text,
                )
            ],
        )
        result = self.security_service.process_diff(collection)
        if result.summary.high or result.summary.critical:
            raise SensitiveContentError("Worklog 包含高风险敏感信息，请移除后重试。")


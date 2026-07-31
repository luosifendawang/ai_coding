"""Web-facing worklog orchestration."""

from __future__ import annotations

from gitpulse.exceptions import RecordNotFoundError, SensitiveContentError
from gitpulse.models.worklog import (
    Worklog,
    WorklogCreate,
    WorklogFilters,
    WorklogUpdate,
)
from gitpulse.services.worklog_service import WorklogService
from gitpulse.web.schemas.worklog import WorklogUpdateRequest, WorklogWriteRequest
from gitpulse.web.services.repository_context_service import RepositoryContextService
from gitpulse.web.services.repository_web_service import RepositoryWebError


class WorklogWebService:
    def __init__(
        self,
        service: WorklogService,
        repository_context: RepositoryContextService,
    ) -> None:
        self.service = service
        self.repository_context = repository_context

    def list(self, filters: WorklogFilters, page: int) -> dict[str, object]:
        items = self.service.list(filters)
        total = self.service.count(filters)
        return {
            "items": [self._payload(item) for item in items],
            "page": page,
            "page_size": filters.limit,
            "total": total,
            "pages": max(1, (total + filters.limit - 1) // filters.limit),
        }

    def create(self, payload: WorklogWriteRequest) -> dict[str, object]:
        repository = self.repository_context.ensure_record()
        request = WorklogCreate(
            repository_id=repository.id,
            work_date=payload.occurred_at.date(),
            occurred_at=payload.occurred_at,
            work_type=payload.type,
            title=payload.title,
            description=payload.description,
            result=payload.result,
            duration_minutes=payload.duration_minutes,
            tags=payload.tags,
            related_commit_hash=payload.related_commit_hash,
            source=payload.source,
        )
        try:
            return self._payload(self.service.create(request))
        except SensitiveContentError as exc:
            raise RepositoryWebError(
                "sensitive_content", str(exc), 422
            ) from exc

    def get(self, worklog_id: str) -> dict[str, object]:
        return self._payload(self._owned(worklog_id))

    def update(
        self, worklog_id: str, payload: WorklogUpdateRequest
    ) -> dict[str, object]:
        self._owned(worklog_id)
        changes = payload.model_dump(exclude_unset=True)
        if "type" in changes:
            changes["work_type"] = changes.pop("type")
        if payload.occurred_at is not None:
            changes["work_date"] = payload.occurred_at.date()
        try:
            return self._payload(
                self.service.update(worklog_id, WorklogUpdate(**changes))
            )
        except SensitiveContentError as exc:
            raise RepositoryWebError(
                "sensitive_content", str(exc), 422
            ) from exc

    def delete(self, worklog_id: str, *, confirmed: bool) -> None:
        if not confirmed:
            raise RepositoryWebError(
                "delete_confirmation_required", "删除工作日志前需要明确确认。"
            )
        self._owned(worklog_id)
        self.service.delete(worklog_id)

    def filters(
        self,
        *,
        date_from,
        date_to,
        work_types,
        tags,
        repository,
        keyword,
        page,
        page_size,
    ) -> WorklogFilters:
        record = self.repository_context.ensure_record()
        if repository and repository not in {
            record.id,
            record.name,
            record.root_path,
        }:
            repository_id = "__no_matching_repository__"
        else:
            repository_id = record.id
        return WorklogFilters(
            repository_id=repository_id,
            date_from=date_from,
            date_to=date_to,
            work_types=work_types,
            tags=tags,
            keyword=keyword,
            limit=page_size,
            offset=(page - 1) * page_size,
        )

    def _owned(self, worklog_id: str) -> Worklog:
        repository = self.repository_context.ensure_record()
        try:
            worklog = self.service.get(worklog_id)
        except RecordNotFoundError as exc:
            raise RepositoryWebError("worklog_not_found", str(exc), 404) from exc
        if worklog.repository_id != repository.id:
            raise RepositoryWebError(
                "worklog_not_found", "未找到工作日志。", 404
            )
        return worklog

    def _payload(self, worklog: Worklog) -> dict[str, object]:
        return {
            "id": worklog.id,
            "repository_id": worklog.repository_id,
            "work_date": worklog.work_date.isoformat(),
            "occurred_at": (
                worklog.occurred_at or worklog.created_at
            ).isoformat(),
            "type": worklog.work_type,
            "title": worklog.title,
            "description": worklog.description,
            "result": worklog.result,
            "duration_minutes": worklog.duration_minutes,
            "tags": worklog.tags,
            "related_commit_hash": worklog.related_commit_hash,
            "source": worklog.source,
            "created_at": worklog.created_at.isoformat(),
            "updated_at": worklog.updated_at.isoformat(),
        }

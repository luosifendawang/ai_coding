"""Authenticated worklog APIs."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import StringConstraints

from gitpulse.web.schemas.worklog import WorklogUpdateRequest, WorklogWriteRequest
from gitpulse.web.security import require_csrf, require_session
from gitpulse.web.services.repository_web_service import RepositoryWebError
from gitpulse.web.sessions import Session

router = APIRouter(prefix="/api/worklogs", tags=["worklogs"])
SessionDependency = Annotated[Session, Depends(require_session)]
CsrfDependency = Annotated[Session, Depends(require_csrf)]
WorkTypeQueryItem = Annotated[str, StringConstraints(max_length=30)]
TagQueryItem = Annotated[str, StringConstraints(max_length=50)]
WorkTypesQuery = Annotated[
    list[WorkTypeQueryItem] | None, Query(alias="type")
]
TagsQuery = Annotated[list[TagQueryItem] | None, Query(alias="tag")]
RepositoryQuery = Annotated[str | None, Query(max_length=500)]
KeywordQuery = Annotated[str | None, Query(max_length=200)]
PageQuery = Annotated[int, Query(ge=1, le=10000)]
PageSizeQuery = Annotated[int, Query(ge=1, le=100)]


@router.get("")
async def list_worklogs(
    request: Request,
    _session: SessionDependency,
    date_from: date | None = None,
    date_to: date | None = None,
    work_types: WorkTypesQuery = None,
    tags: TagsQuery = None,
    repository: RepositoryQuery = None,
    keyword: KeywordQuery = None,
    page: PageQuery = 1,
    page_size: PageSizeQuery = 20,
) -> dict[str, object]:
    if date_from and date_to and date_from > date_to:
        raise RepositoryWebError(
            "invalid_date_range", "开始日期不能晚于结束日期。", 422
        )
    filters = request.app.state.worklog_web_service.filters(
        date_from=date_from,
        date_to=date_to,
        work_types=work_types,
        tags=tags,
        repository=repository,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return request.app.state.worklog_web_service.list(filters, page)


@router.post("", status_code=201)
async def create_worklog(
    request: Request,
    payload: WorklogWriteRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    return request.app.state.worklog_web_service.create(payload)


@router.get("/{worklog_id}")
async def get_worklog(
    request: Request, worklog_id: str, _session: SessionDependency
) -> dict[str, object]:
    return request.app.state.worklog_web_service.get(worklog_id)


@router.put("/{worklog_id}")
async def update_worklog(
    request: Request,
    worklog_id: str,
    payload: WorklogUpdateRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    return request.app.state.worklog_web_service.update(worklog_id, payload)


@router.delete("/{worklog_id}", status_code=204, response_class=Response)
async def delete_worklog(
    request: Request,
    worklog_id: str,
    _session: CsrfDependency,
    confirmed: bool = False,
) -> Response:
    request.app.state.worklog_web_service.delete(
        worklog_id, confirmed=confirmed
    )
    return Response(status_code=204)

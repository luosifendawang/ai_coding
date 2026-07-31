"""Authenticated work-history APIs."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from gitpulse.web.security import require_session
from gitpulse.web.services.repository_web_service import RepositoryWebError
from gitpulse.web.sessions import Session

router = APIRouter(prefix="/api/history", tags=["history"])
SessionDependency = Annotated[Session, Depends(require_session)]
RecordType = Literal["git_commit", "commit_record", "worklog"]
RecordTypesQuery = Annotated[
    list[RecordType] | None, Query(alias="record_type")
]
RepositoryQuery = Annotated[str | None, Query(max_length=500)]
TagQuery = Annotated[str | None, Query(max_length=50)]
CommitTypeQuery = Annotated[str | None, Query(max_length=30)]
KeywordQuery = Annotated[str | None, Query(max_length=200)]
AuthorQuery = Annotated[str | None, Query(max_length=320)]
PageQuery = Annotated[int, Query(ge=1, le=10000)]
PageSizeQuery = Annotated[int, Query(ge=1, le=100)]


@router.get("")
async def history(
    request: Request,
    _session: SessionDependency,
    date_from: date | None = None,
    date_to: date | None = None,
    record_types: RecordTypesQuery = None,
    repository: RepositoryQuery = None,
    tag: TagQuery = None,
    commit_type: CommitTypeQuery = None,
    keyword: KeywordQuery = None,
    author: AuthorQuery = None,
    page: PageQuery = 1,
    page_size: PageSizeQuery = 30,
) -> dict[str, object]:
    _validate_range(date_from, date_to)
    return request.app.state.history_web_service.query(
        date_from=date_from,
        date_to=date_to,
        record_types=record_types,
        repository=repository,
        tag=tag,
        commit_type=commit_type,
        keyword=keyword,
        author=author,
        page=page,
        page_size=page_size,
    )


@router.get("/stats")
async def history_stats(
    request: Request,
    _session: SessionDependency,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, object]:
    _validate_range(date_from, date_to)
    result = request.app.state.history_web_service.query(
        date_from=date_from,
        date_to=date_to,
        record_types=None,
        repository=None,
        tag=None,
        commit_type=None,
        keyword=None,
        author=None,
        page=1,
        page_size=1,
    )
    return result["stats"]


@router.get("/export")
async def export_history(
    request: Request,
    _session: SessionDependency,
    format: Literal["markdown", "json", "csv"] = "markdown",
    date_from: date | None = None,
    date_to: date | None = None,
    record_types: RecordTypesQuery = None,
    repository: RepositoryQuery = None,
    tag: TagQuery = None,
    commit_type: CommitTypeQuery = None,
    keyword: KeywordQuery = None,
    author: AuthorQuery = None,
) -> Response:
    _validate_range(date_from, date_to)
    content, media_type, filename = request.app.state.history_web_service.export(
        export_format=format,
        date_from=date_from,
        date_to=date_to,
        record_types=record_types,
        repository=repository,
        tag=tag,
        commit_type=commit_type,
        keyword=keyword,
        author=author,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _validate_range(date_from: date | None, date_to: date | None) -> None:
    if date_from and date_to and date_from > date_to:
        raise RepositoryWebError(
            "invalid_date_range", "开始日期不能晚于结束日期。", 422
        )

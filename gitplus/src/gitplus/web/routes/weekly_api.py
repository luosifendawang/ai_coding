"""Authenticated weekly report APIs."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response

from gitplus.web.schemas.weekly import (
    WeeklyGenerateWebRequest,
    WeeklyRangeRequest,
    WeeklyUpdateRequest,
    WeeklyVersionRequest,
)
from gitplus.web.security import require_csrf, require_session
from gitplus.web.sessions import Session

router = APIRouter(prefix="/api/weekly", tags=["weekly"])
SessionDependency = Annotated[Session, Depends(require_session)]
CsrfDependency = Annotated[Session, Depends(require_csrf)]
PageQuery = Annotated[int, Query(ge=1, le=10000)]
PageSizeQuery = Annotated[int, Query(ge=1, le=100)]
VersionQuery = Annotated[int, Query(ge=1)]
StatusQuery = Annotated[
    Literal["draft", "confirmed", "exported", "sent"] | None,
    Query(),
]


@router.post("/preview")
async def preview_weekly(
    request: Request,
    payload: WeeklyRangeRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    return request.app.state.weekly_web_service.preview(payload)


@router.post("/generate", status_code=201)
async def generate_weekly(
    request: Request,
    payload: WeeklyGenerateWebRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    return request.app.state.weekly_web_service.generate(payload)


@router.get("")
async def list_weekly(
    request: Request,
    _session: SessionDependency,
    status: StatusQuery = None,
    page: PageQuery = 1,
    page_size: PageSizeQuery = 20,
) -> dict[str, object]:
    return request.app.state.weekly_web_service.list_reports(
        status=status, page=page, page_size=page_size
    )


@router.get("/{report_id}")
async def get_weekly(
    request: Request, report_id: str, _session: SessionDependency
) -> dict[str, object]:
    return request.app.state.weekly_web_service.get(report_id)


@router.put("/{report_id}")
async def update_weekly(
    request: Request,
    report_id: str,
    payload: WeeklyUpdateRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    return request.app.state.weekly_web_service.update(
        report_id,
        expected_version=payload.version,
        edited=payload.report,
    )


@router.delete("/{report_id}", status_code=204, response_class=Response)
async def delete_weekly(
    request: Request,
    report_id: str,
    _session: CsrfDependency,
    version: VersionQuery,
    confirmed: bool = False,
) -> Response:
    request.app.state.weekly_web_service.delete(
        report_id,
        expected_version=version,
        confirmed=confirmed,
    )
    return Response(status_code=204)


@router.post("/{report_id}/confirm")
async def confirm_weekly(
    request: Request,
    report_id: str,
    payload: WeeklyVersionRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    return request.app.state.weekly_web_service.confirm(
        report_id, expected_version=payload.version
    )


@router.post("/{report_id}/reopen")
async def reopen_weekly(
    request: Request,
    report_id: str,
    payload: WeeklyVersionRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    return request.app.state.weekly_web_service.reopen(
        report_id, expected_version=payload.version
    )


@router.get("/{report_id}/export")
async def export_weekly(
    request: Request,
    report_id: str,
    _session: SessionDependency,
    format: Literal["markdown", "text", "json"] = "markdown",
) -> Response:
    content, media_type, filename = (
        request.app.state.weekly_web_service.export(report_id, format)
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

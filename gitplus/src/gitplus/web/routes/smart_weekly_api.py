"""API endpoints for the independent smart weekly assistant."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from gitplus.models.smart_weekly import (
    SmartWeeklyGenerateRequest,
    SmartWeeklyRefineRequest,
    SmartWeeklySaveRequest,
    SmartWeeklyUpdateRequest,
)
from gitplus.web.security import require_session
from gitplus.web.services.repository_web_service import RepositoryWebError
from gitplus.web.sessions import Session

router = APIRouter(prefix="/api/smart-weekly", tags=["smart-weekly"])
SessionDependency = Annotated[Session, Depends(require_session)]


@router.get("/sources")
async def sources(
    request: Request, _session: SessionDependency, date_from: date, date_to: date
) -> dict[str, object]:
    _range(date_from, date_to)
    items = request.app.state.smart_weekly_service.sources(date_from, date_to)
    return {
        "items": [item.model_dump(mode="json") for item in items],
        "total": len(items),
    }


@router.post("/generate")
async def generate(
    request: Request, payload: SmartWeeklyGenerateRequest, _session: SessionDependency
) -> dict[str, object]:
    _range(payload.date_from, payload.date_to)
    try:
        draft = request.app.state.smart_weekly_service.generate(
            payload.date_from,
            payload.date_to,
            payload.source_ids,
            use_ai=payload.use_ai,
            extra_context=payload.extra_context,
        )
    except ValueError as exc:
        raise RepositoryWebError("smart_weekly_invalid", str(exc), 422) from exc
    return {"draft": draft.model_dump(mode="json")}


@router.post("/refine")
async def refine(
    request: Request, payload: SmartWeeklyRefineRequest, _session: SessionDependency
) -> dict[str, object]:
    try:
        draft = request.app.state.smart_weekly_service.refine(
            payload.draft, payload.instruction
        )
    except Exception as exc:
        raise RepositoryWebError(
            "smart_weekly_refine_failed", f"智能调整失败：{exc}", 422
        ) from exc
    return {"draft": draft.model_dump(mode="json")}


@router.post("/save")
async def save(
    request: Request, payload: SmartWeeklySaveRequest, _session: SessionDependency
) -> dict[str, str]:
    return {"id": request.app.state.smart_weekly_service.save(payload.draft)}


@router.post("/export")
async def export(
    payload: SmartWeeklySaveRequest, _session: SessionDependency
) -> Response:
    filename = f"smart-weekly-{payload.draft.date_from}-{payload.draft.date_to}.md"
    return Response(
        payload.draft.markdown.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports")
async def reports(
    request: Request,
    _session: SessionDependency,
    status: str | None = None,
) -> dict[str, object]:
    if status not in {None, "draft", "confirmed"}:
        raise RepositoryWebError("smart_weekly_invalid_status", "周报状态无效。", 422)
    items = request.app.state.smart_weekly_service.list_reports(status)
    return {"items": items, "total": len(items)}


@router.get("/reports/{report_id}")
async def report_detail(
    request: Request, report_id: str, _session: SessionDependency
) -> dict[str, object]:
    return _report_action(
        lambda: request.app.state.smart_weekly_service.get_report(report_id)
    )


@router.put("/reports/{report_id}")
async def update_report(
    request: Request,
    report_id: str,
    payload: SmartWeeklyUpdateRequest,
    _session: SessionDependency,
) -> dict[str, object]:
    return _report_action(
        lambda: request.app.state.smart_weekly_service.update_report(
            report_id, payload.title, payload.markdown, payload.expected_version
        )
    )


@router.post("/reports/{report_id}/confirm")
async def confirm_report(
    request: Request, report_id: str, _session: SessionDependency
) -> dict[str, object]:
    return _report_action(
        lambda: request.app.state.smart_weekly_service.set_status(
            report_id, "confirmed"
        )
    )


@router.post("/reports/{report_id}/reopen")
async def reopen_report(
    request: Request, report_id: str, _session: SessionDependency
) -> dict[str, object]:
    return _report_action(
        lambda: request.app.state.smart_weekly_service.set_status(report_id, "draft")
    )


@router.delete("/reports/{report_id}")
async def delete_report(
    request: Request, report_id: str, _session: SessionDependency
) -> dict[str, bool]:
    _report_action(
        lambda: request.app.state.smart_weekly_service.delete_report(report_id)
    )
    return {"deleted": True}


def _report_action(action):
    try:
        return action()
    except LookupError as exc:
        raise RepositoryWebError("smart_weekly_not_found", str(exc), 404) from exc
    except ValueError as exc:
        raise RepositoryWebError("smart_weekly_conflict", str(exc), 409) from exc


def _range(date_from: date, date_to: date) -> None:
    if date_from > date_to or (date_to - date_from).days > 31:
        raise RepositoryWebError(
            "smart_weekly_invalid_range", "日期范围无效，且最多支持 31 天。", 422
        )

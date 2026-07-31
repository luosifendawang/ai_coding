"""Authenticated Feishu notification APIs."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request

from gitpulse.web.schemas.notification import (
    NotificationPreviewRequest,
    NotificationRetryRequest,
    NotificationSendRequest,
    NotificationTestRequest,
)
from gitpulse.web.security import require_csrf, require_session
from gitpulse.web.sessions import Session

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
SessionDependency = Annotated[Session, Depends(require_session)]
CsrfDependency = Annotated[Session, Depends(require_csrf)]
PageQuery = Annotated[int, Query(ge=1, le=10000)]
PageSizeQuery = Annotated[int, Query(ge=1, le=100)]
StatusQuery = Annotated[
    Literal[
        "pending",
        "previewed",
        "confirmed",
        "sending",
        "sent",
        "failed",
        "unknown",
        "cancelled",
        "duplicate_blocked",
    ]
    | None,
    Query(),
]


@router.get("/config-status")
async def config_status(
    request: Request, _session: SessionDependency
) -> dict[str, object]:
    return request.app.state.notification_web_service.config_status()


@router.post("/test")
async def test_notification(
    request: Request,
    payload: NotificationTestRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    return request.app.state.notification_web_service.test(payload)


@router.post("/preview")
async def preview_notification(
    request: Request,
    payload: NotificationPreviewRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    return request.app.state.notification_web_service.preview(payload)


@router.post("/send")
async def send_notification(
    request: Request,
    payload: NotificationSendRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    return request.app.state.notification_web_service.send(payload)


@router.get("")
async def list_notifications(
    request: Request,
    _session: SessionDependency,
    status: StatusQuery = None,
    page: PageQuery = 1,
    page_size: PageSizeQuery = 20,
) -> dict[str, object]:
    return request.app.state.notification_web_service.list_records(
        status=status, page=page, page_size=page_size
    )


@router.get("/{notification_id}")
async def get_notification(
    request: Request,
    notification_id: str,
    _session: SessionDependency,
) -> dict[str, object]:
    return request.app.state.notification_web_service.get_record(notification_id)


@router.post("/{notification_id}/retry")
async def retry_notification(
    request: Request,
    notification_id: str,
    payload: NotificationRetryRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    return request.app.state.notification_web_service.retry(notification_id, payload)

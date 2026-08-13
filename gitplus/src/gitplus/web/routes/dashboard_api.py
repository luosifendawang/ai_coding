"""Authenticated dashboard APIs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from gitplus.web.security import require_session
from gitplus.web.sessions import Session

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
SessionDependency = Annotated[Session, Depends(require_session)]


@router.get("")
async def dashboard(
    request: Request, _session: SessionDependency
) -> dict[str, object]:
    return request.app.state.dashboard_service.summary()

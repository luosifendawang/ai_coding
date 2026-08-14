"""Authenticated configuration APIs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from gitplus.web.schemas.config import ConfigUpdateRequest, SecretUpdateAction
from gitplus.web.security import require_csrf, require_session
from gitplus.web.services.config_web_service import ConfigConflictError
from gitplus.web.sessions import Session

router = APIRouter(prefix="/api/config", tags=["config"])
SessionDependency = Annotated[Session, Depends(require_session)]
CsrfDependency = Annotated[Session, Depends(require_csrf)]


@router.get("/effective")
async def effective(request: Request, _session: SessionDependency) -> dict[str, object]:
    return request.app.state.config_service.get_effective_config()


@router.get("")
async def current_config(
    request: Request, _session: SessionDependency
) -> dict[str, object]:
    return request.app.state.config_service.get_effective_config()


@router.get("/sources")
async def sources(request: Request, _session: SessionDependency) -> dict[str, object]:
    return request.app.state.config_service.sources()


@router.post("/validate")
async def validate(
    request: Request,
    payload: ConfigUpdateRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    return request.app.state.config_service.validate_update(payload)


@router.post("/preview")
async def preview(
    request: Request,
    payload: ConfigUpdateRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    return request.app.state.config_service.preview_update(payload)


@router.put("")
async def save(
    request: Request,
    payload: ConfigUpdateRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    try:
        saved = request.app.state.config_service.save_update(payload)
        request.app.state.refresh_runtime_config()
        return saved
    except ConfigConflictError as exc:
        raise HTTPException(status_code=409, detail="config_changed") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="config_write_failed") from exc


@router.post("/restore")
async def restore(
    request: Request,
    _session: CsrfDependency,
) -> dict[str, object]:
    try:
        return request.app.state.config_service.restore_latest()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="config_not_found") from exc


@router.post("/test-ai")
async def test_ai(
    request: Request,
    payload: ConfigUpdateRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    validation = request.app.state.config_service.validate_update(payload)
    if not validation["valid"]:
        raise HTTPException(status_code=422, detail="config_validation_failed")
    config = request.app.state.config_service.config_for_request(payload).ai
    secret = _temporary_secret(request, payload, "ai.api_key")
    return request.app.state.connection_service.test_ai(config, secret)


@router.post("/test-storage")
async def test_storage(
    request: Request,
    payload: ConfigUpdateRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    config = request.app.state.config_service.config_for_request(payload).storage
    return request.app.state.connection_service.test_storage(
        config,
        request.app.state.config_service.paths.project_root,
    )


def _temporary_secret(
    request: Request, payload: ConfigUpdateRequest, path: str
) -> str | None:
    update = payload.secret_updates.get(path)
    if update is None or update.action == SecretUpdateAction.KEEP:
        return request.app.state.config_service.secret_value(path)
    if update.action == SecretUpdateAction.DELETE:
        return None
    return update.value.get_secret_value() if update.value is not None else None

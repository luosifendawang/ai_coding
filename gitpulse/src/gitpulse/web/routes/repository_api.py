"""Authenticated Git workbench APIs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from gitpulse.web.schemas.repository import (
    CommitCreateRequest,
    CommitGenerateRequest,
    PathsRequest,
    SecurityScanRequest,
)
from gitpulse.web.security import require_csrf, require_session
from gitpulse.web.sessions import Session

router = APIRouter(prefix="/api/repository", tags=["repository"])
SessionDependency = Annotated[Session, Depends(require_session)]
CsrfDependency = Annotated[Session, Depends(require_csrf)]


@router.get("/status")
async def status(request: Request, _session: SessionDependency) -> dict[str, object]:
    result = request.app.state.repository_service.status()
    _audit(request, "repository_status_read", True, len(result["files"]))
    return result


@router.get("/revision")
async def revision(
    request: Request,
    _session: SessionDependency,
    current: str | None = None,
) -> dict[str, object]:
    value = request.app.state.repository_service.status()["revision"]
    return {"revision": value, "changed": bool(current and current != value)}


@router.get("/diff")
async def diff(
    request: Request,
    _session: SessionDependency,
    path: str = Query(min_length=1),
    source: str = "unstaged",
    context: int | None = None,
) -> dict[str, object]:
    result = request.app.state.diff_service.read(path, source, context)
    _audit(request, "diff_read", True, 1)
    return result


@router.post("/stage")
async def stage(
    request: Request, payload: PathsRequest, _session: CsrfDependency
) -> dict[str, object]:
    result = request.app.state.repository_service.stage(payload.paths, payload.revision)
    _audit(request, "files_staged", True, len(payload.paths))
    return result


@router.post("/unstage")
async def unstage(
    request: Request, payload: PathsRequest, _session: CsrfDependency
) -> dict[str, object]:
    result = request.app.state.repository_service.unstage(
        payload.paths, payload.revision
    )
    _audit(request, "files_unstaged", True, len(payload.paths))
    return result


@router.post("/security-scan")
async def security_scan(
    request: Request,
    payload: SecurityScanRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    result = request.app.state.commit_web_service.security_scan(payload.revision)
    _audit(request, "security_scan", True)
    return result


@router.post("/commit/generate")
async def generate_commit(
    request: Request,
    payload: CommitGenerateRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    result = request.app.state.commit_web_service.generate(
        revision=payload.revision,
        scan_id=payload.scan_id,
        context=payload.context,
    )
    _audit(request, "commit_generated", True)
    return result


@router.post("/commit")
async def create_commit(
    request: Request,
    payload: CommitCreateRequest,
    _session: CsrfDependency,
) -> dict[str, object]:
    result = request.app.state.commit_web_service.commit(
        generation_id=payload.generation_id,
        revision=payload.repository_revision,
        selected_candidate=payload.selected_candidate,
        subject=payload.subject,
        body=payload.body,
        footer=payload.footer,
        confirmed=payload.confirmed,
    )
    _audit(request, "commit_created", True)
    return result


def _audit(
    request: Request, operation: str, success: bool, file_count: int = 0
) -> None:
    request.app.state.audit_service.record(
        operation,
        repository=str(request.app.state.repository_service.root),
        success=success,
        file_count=file_count,
        session_id=request.cookies.get("gitpulse_session"),
    )

"""Local Web health endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from gitplus import __version__
from gitplus.storage.migrations.manager import CURRENT_SCHEMA_VERSION, MigrationManager
from gitplus.web.security import require_session
from gitplus.web.sessions import Session

router = APIRouter(tags=["health"])
SessionDependency = Annotated[Session, Depends(require_session)]


@router.get("/health")
async def legacy_health(request: Request) -> dict[str, object]:
    return await health(request)


@router.get("/api/health")
async def health(request: Request) -> dict[str, object]:
    database = request.app.state.database
    try:
        database.initialize()
        version = MigrationManager(database.engine).current_version()
        database_ok = version == CURRENT_SCHEMA_VERSION
    except Exception:  # noqa: BLE001
        version = None
        database_ok = False
    return {
        "version": __version__,
        "status": "ok" if database_ok else "degraded",
        "web": "running",
        "database": {
            "ok": database_ok,
            "schema_version": version,
            "expected_schema_version": CURRENT_SCHEMA_VERSION,
        },
    }


@router.get("/api/health/details")
async def health_details(
    request: Request, _session: SessionDependency
) -> dict[str, object]:
    dashboard = request.app.state.dashboard_service.summary()
    config_status = request.app.state.config_service.get_effective_config()
    sources = request.app.state.config_service.sources()
    return {
        "version": __version__,
        "repository": dashboard["repository"],
        "git_summary": dashboard["git_summary"],
        "config": {
            "revision": config_status["revision"],
            "sources": config_status["sources"],
        },
        "ai": dashboard["ai"],
        "database": dashboard["database"],
        "writable": {
            "database_dir": dashboard["database"].get("writable")
            if isinstance(dashboard["database"], dict)
            else False,
            "config": sources,
        },
        "warnings": dashboard["warnings"],
    }

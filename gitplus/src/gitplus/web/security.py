"""Local-only request security for the Web console."""

from __future__ import annotations

import secrets
from typing import Callable
from urllib.parse import urlparse

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from gitplus.web.sessions import Session, SessionStore

SAFE_HOSTS = {"127.0.0.1", "localhost", "::1"}
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class LocalRequestSecurityMiddleware(BaseHTTPMiddleware):
    """Reject non-local hosts and cross-origin writes before routing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        host = request.url.hostname or ""
        if host not in SAFE_HOSTS:
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "unauthorized",
                        "message": "仅允许本机访问。",
                        "details": [],
                    }
                },
            )
        if request.method in UNSAFE_METHODS:
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")
            candidate = origin or referer
            source = urlparse(candidate) if candidate else None
            source_port = (
                source.port
                if source and source.port
                else (443 if source and source.scheme == "https" else 80)
            )
            request_port = request.url.port or (
                443 if request.url.scheme == "https" else 80
            )
            if (
                source is None
                or source.hostname not in SAFE_HOSTS
                or source_port != request_port
            ):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "csrf_failed",
                            "message": "请求来源校验失败。",
                            "details": [],
                        }
                    },
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response


async def require_session(request: Request) -> Session:
    store: SessionStore = request.app.state.sessions
    session = store.get(request.cookies.get("gitplus_session"))
    if session is None:
        raise HTTPException(status_code=403, detail="unauthorized")
    return session


async def require_csrf(request: Request) -> Session:
    session = await require_session(request)
    token = request.headers.get("x-csrf-token", "")
    if not token or not secrets.compare_digest(token, session.csrf_token):
        raise HTTPException(status_code=403, detail="csrf_failed")
    return session

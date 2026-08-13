"""HTML page and local authentication routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from gitplus import __version__
from gitplus.web.security import require_session

router = APIRouter()


@router.get("/auth/local")
async def local_auth(request: Request, token: str) -> RedirectResponse:
    authenticated = request.app.state.sessions.authenticate(token)
    if authenticated is None:
        raise HTTPException(status_code=403, detail="unauthorized")
    session_id, _session = authenticated
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        "gitplus_session",
        session_id,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=request.app.state.sessions.timeout_minutes * 60,
        path="/",
    )
    return response


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    session = await require_session(request)
    effective = request.app.state.config_service.get_effective_config()
    dashboard_data = request.app.state.dashboard_service.summary()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "version": __version__,
            "project": effective["project"],
            "effective": effective,
            "dashboard": dashboard_data,
            "csrf_token": session.csrf_token,
            "active_page": "dashboard",
        },
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings(request: Request) -> HTMLResponse:
    session = await require_session(request)
    effective = request.app.state.config_service.get_effective_config()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "version": __version__,
            "project": effective["project"],
            "csrf_token": session.csrf_token,
            "active_page": "settings",
        },
    )


@router.get("/repository", response_class=HTMLResponse)
async def repository(request: Request) -> HTMLResponse:
    session = await require_session(request)
    effective = request.app.state.config_service.get_effective_config()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="repository.html",
        context={
            "version": __version__,
            "project": effective["project"],
            "csrf_token": session.csrf_token,
            "active_page": "repository",
        },
    )


@router.get("/worklogs", response_class=HTMLResponse)
async def worklogs(request: Request) -> HTMLResponse:
    session = await require_session(request)
    effective = request.app.state.config_service.get_effective_config()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="worklogs.html",
        context={
            "version": __version__,
            "project": effective["project"],
            "csrf_token": session.csrf_token,
            "active_page": "worklogs",
        },
    )


@router.get("/history", response_class=HTMLResponse)
async def history(request: Request) -> HTMLResponse:
    session = await require_session(request)
    effective = request.app.state.config_service.get_effective_config()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "version": __version__,
            "project": effective["project"],
            "csrf_token": session.csrf_token,
            "active_page": "history",
        },
    )


@router.get("/weekly", response_class=HTMLResponse)
async def weekly(request: Request) -> HTMLResponse:
    session = await require_session(request)
    effective = request.app.state.config_service.get_effective_config()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="weekly.html",
        context={
            "version": __version__,
            "project": effective["project"],
            "csrf_token": session.csrf_token,
            "active_page": "weekly",
        },
    )


@router.get("/weekly/{report_id}", response_class=HTMLResponse)
async def weekly_detail(request: Request, report_id: str) -> HTMLResponse:
    session = await require_session(request)
    effective = request.app.state.config_service.get_effective_config()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="weekly_detail.html",
        context={
            "version": __version__,
            "project": effective["project"],
            "csrf_token": session.csrf_token,
            "active_page": "weekly",
            "report_id": report_id,
        },
    )


@router.get("/notifications", response_class=HTMLResponse)
async def notifications(request: Request) -> HTMLResponse:
    session = await require_session(request)
    effective = request.app.state.config_service.get_effective_config()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="notifications.html",
        context={
            "version": __version__,
            "project": effective["project"],
            "csrf_token": session.csrf_token,
            "active_page": "notifications",
        },
    )


@router.get("/notifications/{notification_id}", response_class=HTMLResponse)
async def notification_detail(
    request: Request, notification_id: str
) -> HTMLResponse:
    session = await require_session(request)
    effective = request.app.state.config_service.get_effective_config()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="notification_detail.html",
        context={
            "version": __version__,
            "project": effective["project"],
            "csrf_token": session.csrf_token,
            "active_page": "notifications",
            "notification_id": notification_id,
        },
    )

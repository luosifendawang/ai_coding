"""FastAPI application factory for the local GitPulse console."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from gitpulse import __version__
from gitpulse.ai.mock_provider import MockLLMProvider
from gitpulse.ai.openai_provider import OpenAICompatibleProvider
from gitpulse.ai.provider import LLMProvider
from gitpulse.ai.weekly_generator import WeeklyGenerator
from gitpulse.config import GitPulseConfig
from gitpulse.services.git_service import GitService
from gitpulse.services.history_service import HistoryService
from gitpulse.services.security_service import SecurityService
from gitpulse.services.weekly_service import WeeklyService
from gitpulse.services.worklog_service import WorklogService
from gitpulse.storage.database import Database
from gitpulse.web.routes import (
    config_api,
    dashboard_api,
    health_api,
    history_api,
    notification_api,
    pages,
    repository_api,
    weekly_api,
    worklog_api,
)
from gitpulse.web.security import LocalRequestSecurityMiddleware
from gitpulse.web.services.commit_web_service import CommitWebService
from gitpulse.web.services.config_web_service import ConfigWebService
from gitpulse.web.services.connection_test_service import ConnectionTestService
from gitpulse.web.services.dashboard_web_service import DashboardWebService
from gitpulse.web.services.diff_web_service import DiffWebService
from gitpulse.web.services.history_web_service import HistoryWebService
from gitpulse.web.services.notification_web_service import NotificationWebService
from gitpulse.web.services.operation_audit_service import OperationAuditService
from gitpulse.web.services.repository_context_service import RepositoryContextService
from gitpulse.web.services.repository_web_service import (
    RepositoryWebError,
    RepositoryWebService,
)
from gitpulse.web.services.weekly_web_service import WeeklyWebService
from gitpulse.web.services.worklog_web_service import WorklogWebService
from gitpulse.web.sessions import SessionStore


def create_app(
    project_root: Path | None = None,
    *,
    access_token: str | None = None,
    user_config_path: Path | None = None,
    secrets_path: Path | None = None,
    connection_service: ConnectionTestService | None = None,
    database: Database | None = None,
    commit_provider: LLMProvider | None = None,
) -> FastAPI:
    """Create a local-only application with isolated runtime session state."""
    root = (project_root or Path.cwd()).resolve()
    package_dir = Path(__file__).parent
    config_service = ConfigWebService(
        root,
        user_path=user_config_path,
        secrets_path=secrets_path,
    )
    config = GitPulseConfig.model_validate(
        config_service.get_effective_config()["config"]
    )
    ai_secret = config_service.secret_value("ai.api_key")
    if ai_secret:
        config.ai = config.ai.model_copy(update={"api_key": ai_secret})
    feishu_updates = {}
    for key in ["webhook", "secret", "app_secret"]:
        value = config_service.secret_value(f"feishu.{key}")
        if value:
            feishu_updates[key] = value
    if feishu_updates:
        config.feishu = config.feishu.model_copy(update=feishu_updates)
    web_config = config.web
    repository_service = RepositoryWebService(root)
    database_path = config.storage.database_path
    if not database_path.is_absolute():
        database_path = root / database_path
    active_database = database or Database(
        database_path, timeout_seconds=config.storage.sqlite_timeout_seconds
    )
    app = FastAPI(
        title="GitPulse Web",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.sessions = SessionStore(
        access_token=access_token,
        timeout_minutes=web_config.session_timeout_minutes,
    )
    app.state.config_service = config_service
    app.state.connection_service = connection_service or ConnectionTestService()
    app.state.repository_service = repository_service
    app.state.diff_service = DiffWebService(
        repository_service, config.web.diff, config.security
    )
    app.state.database = active_database
    app.state.commit_web_service = CommitWebService(
        repository_service,
        config,
        active_database,
        provider=commit_provider,
    )
    app.state.audit_service = OperationAuditService(active_database)
    repository_context = RepositoryContextService(
        repository_service, active_database
    )
    worklog_service = WorklogService(active_database)
    app.state.worklog_web_service = WorklogWebService(
        worklog_service, repository_context
    )
    app.state.history_web_service = HistoryWebService(
        repository_service,
        repository_context,
        HistoryService(active_database),
        worklog_service,
    )
    weekly_provider = commit_provider
    if weekly_provider is None:
        weekly_provider = (
            MockLLMProvider()
            if config.ai.provider == "mock"
            else OpenAICompatibleProvider(config.ai)
        )
    weekly_service = WeeklyService(
        active_database,
        git_service=GitService(
            path=root,
            diff_config=config.diff,
        ),
        config=config.weekly,
        generator=WeeklyGenerator(
            weekly_provider,
            model=config.ai.model,
            temperature=config.ai.temperature,
            top_p=config.ai.top_p,
            max_output_tokens=config.ai.max_output_tokens,
        ),
        security_service=SecurityService(config.security),
    )
    app.state.weekly_web_service = WeeklyWebService(
        weekly_service, repository_context
    )
    app.state.notification_web_service = NotificationWebService(
        active_database,
        repository_context,
        config.feishu,
        security_service=SecurityService(config.security),
    )
    app.state.dashboard_service = DashboardWebService(
        repository_service,
        repository_context,
        active_database,
        config,
    )
    app.state.templates = Jinja2Templates(directory=package_dir / "templates")
    app.mount("/static", StaticFiles(directory=package_dir / "static"), name="static")
    app.add_middleware(LocalRequestSecurityMiddleware)
    app.include_router(health_api.router)
    app.include_router(pages.router)
    app.include_router(dashboard_api.router)
    app.include_router(config_api.router)
    app.include_router(repository_api.router)
    app.include_router(worklog_api.router)
    app.include_router(history_api.router)
    app.include_router(weekly_api.router)
    app.include_router(notification_api.router)
    app.add_exception_handler(HTTPException, _http_error)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _http_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(RepositoryWebError, _repository_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _internal_error)
    return app


async def _http_error(_request: Request, exc: HTTPException) -> Response:
    if not _request.url.path.startswith("/api/"):
        return _html_error(
            _request,
            status_code=exc.status_code,
            title=_error_title(exc.status_code),
            message=_error_message(str(exc.detail), exc.status_code),
        )
    code = str(exc.detail)
    messages = {
        "unauthorized": "需要通过本地启动链接进入控制台。",
        "csrf_failed": "CSRF 校验失败。",
        "config_changed": "配置文件已被其他程序修改，请重新加载后再保存。",
        "config_not_found": "没有找到可恢复的配置备份。",
        "config_validation_failed": "配置校验失败。",
        "config_write_failed": "配置写入失败，原文件未被修改。",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code if code in messages else "config_validation_failed",
                "message": messages.get(code, code),
                "details": [],
            }
        },
    )


async def _internal_error(_request: Request, _exc: Exception) -> Response:
    if not _request.url.path.startswith("/api/"):
        return _html_error(
            _request,
            status_code=500,
            title="服务处理失败",
            message="请检查本地日志后重试。",
        )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "服务处理失败，请检查本地日志。",
                "details": [],
            }
        },
    )


async def _repository_error(request: Request, exc: RepositoryWebError) -> Response:
    if hasattr(request.app.state, "audit_service"):
        request.app.state.audit_service.record(
            request.url.path.rsplit("/", 1)[-1] or "repository_operation",
            repository=str(request.app.state.repository_service.root),
            success=False,
            error_code=exc.code,
            session_id=request.cookies.get("gitpulse_session"),
        )
    if not request.url.path.startswith("/api/"):
        return _html_error(
            request,
            status_code=exc.status_code,
            title=_error_title(exc.status_code),
            message=str(exc),
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": str(exc),
                "details": [],
            }
        },
    )


async def _validation_error(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "request_validation_failed",
                "message": "请求参数校验失败。",
                "details": [
                    {
                        "path": ".".join(str(item) for item in error["loc"][1:]),
                        "message": error["msg"],
                    }
                    for error in exc.errors()
                ],
            }
        },
    )


def _html_error(
    request: Request, *, status_code: int, title: str, message: str
) -> Response:
    templates = request.app.state.templates
    project = {"name": "GitPulse", "root": str(request.app.state.repository_service.root)}
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        status_code=status_code,
        context={
            "version": __version__,
            "project": project,
            "csrf_token": "",
            "active_page": "",
            "status_code": status_code,
            "title": title,
            "message": message,
        },
    )


def _error_title(status_code: int) -> str:
    return {
        403: "访问被拒绝",
        404: "页面不存在",
        409: "状态已变化",
        500: "服务处理失败",
    }.get(status_code, "请求失败")


def _error_message(code: str, status_code: int) -> str:
    messages = {
        "unauthorized": "需要通过本地启动链接进入控制台。",
        "csrf_failed": "CSRF 校验失败。",
    }
    return messages.get(code, _error_title(status_code))

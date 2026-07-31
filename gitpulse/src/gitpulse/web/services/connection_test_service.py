"""Safe connection and local path diagnostics for Web settings."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from time import perf_counter
from typing import Callable

from gitpulse.ai.openai_provider import OpenAICompatibleProvider
from gitpulse.ai.provider import LLMProvider
from gitpulse.config import AIConfig, FeishuConfig, StorageConfig
from gitpulse.integrations.feishu_client import FeishuClient
from gitpulse.models.ai import AIMessage, AIRequest


class ConnectionTestService:
    """Run minimal tests without exposing project content or credentials."""

    def __init__(
        self,
        provider_factory: Callable[[AIConfig], LLMProvider] | None = None,
        feishu_client_factory: (
            Callable[[str, str, str | None, FeishuConfig], FeishuClient] | None
        ) = None,
    ) -> None:
        self.provider_factory = provider_factory or (
            lambda config: OpenAICompatibleProvider(config)
        )
        self.feishu_client_factory = feishu_client_factory or (
            lambda app_id, app_secret, receive_id, config: FeishuClient(
                app_id, app_secret, receive_id, config
            )
        )

    def test_ai(self, config: AIConfig, secret: str | None) -> dict[str, object]:
        effective = config.model_copy(
            update={
                "api_key": secret or config.api_key,
                "timeout_seconds": min(config.timeout_seconds, 15),
            }
        )
        start = perf_counter()
        try:
            response = self.provider_factory(effective).generate(
                AIRequest(
                    model=effective.model,
                    messages=[
                        AIMessage(
                            role="user",
                            content='Return only this JSON object: {"status":"ok"}',
                        )
                    ],
                    temperature=0,
                    top_p=1,
                    max_output_tokens=32,
                    response_schema={
                        "type": "object",
                        "properties": {"status": {"type": "string"}},
                        "required": ["status"],
                    },
                )
            )
            success = bool(response.content)
            return {
                "success": success,
                "provider": effective.provider,
                "model": effective.model,
                "latency_ms": int((perf_counter() - start) * 1000),
                "message": "连接成功" if success else "AI Provider 返回空响应",
            }
        except Exception as exc:  # noqa: BLE001 - provider adapters expose different exception types
            error_type = self._error_type(exc)
            messages = {
                "authentication": "AI Provider 鉴权失败",
                "timeout": "AI Provider 请求超时",
                "rate_limit": "AI Provider 请求频率受限",
                "provider": "AI Provider 连接失败",
            }
            return {
                "success": False,
                "error_type": error_type,
                "message": messages[error_type],
                "latency_ms": int((perf_counter() - start) * 1000),
            }

    def test_feishu(
        self,
        config: FeishuConfig,
        app_secret: str | None,
    ) -> dict[str, object]:
        if not config.app_id:
            return {"success": False, "message": "尚未配置飞书 App ID"}
        if not app_secret:
            return {"success": False, "message": "尚未配置飞书 App Secret"}
        try:
            result = self.feishu_client_factory(
                config.app_id,
                app_secret,
                config.receive_id,
                config,
            ).test_connection(send_message=False)
            return {
                "success": result.success,
                "host": "open.feishu.cn",
                "message": "飞书应用机器人鉴权成功",
            }
        except Exception:  # noqa: BLE001 - Feishu adapters expose different exception types
            return {"success": False, "message": "飞书应用机器人鉴权失败"}

    def test_storage(
        self, config: StorageConfig, project_root: Path
    ) -> dict[str, object]:
        database = Path(config.database).expanduser()
        if not database.is_absolute():
            database = (project_root / database).resolve()
        report_dir = Path(config.report_dir).expanduser()
        if not report_dir.is_absolute():
            report_dir = (project_root / report_dir).resolve()
        try:
            database.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(
                database, timeout=min(config.sqlite_timeout_seconds, 3)
            ) as connection:
                connection.execute("PRAGMA schema_version").fetchone()
            report_dir.mkdir(parents=True, exist_ok=True)
            probe = report_dir / ".gitpulse-write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return {
                "success": True,
                "database": str(database),
                "report_dir": str(report_dir),
                "message": "数据库和报告目录可用",
            }
        except OSError as exc:
            return {"success": False, "message": str(exc)}

    def _error_type(self, exc: Exception) -> str:
        name = type(exc).__name__.lower()
        if "authentication" in name:
            return "authentication"
        if "timeout" in name:
            return "timeout"
        if "ratelimit" in name:
            return "rate_limit"
        return "provider"

"""Feishu application bot API client."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from time import monotonic, sleep, time
from typing import Callable, ClassVar, Protocol

import httpx

from gitplus import __version__
from gitplus.config import FeishuConfig
from gitplus.exceptions import (
    FeishuAuthenticationError,
    FeishuConnectionError,
    FeishuRateLimitError,
    FeishuRequestError,
    FeishuResponseError,
    FeishuTimeoutError,
    NotificationContentTooLargeError,
)
from gitplus.integrations.feishu_response import FeishuResponseParser
from gitplus.models.feishu import FeishuSendResponse


class Sleeper(Protocol):
    def sleep(self, seconds: float) -> None:
        """Sleep for retry backoff."""


class SystemSleeper:
    def sleep(self, seconds: float) -> None:
        sleep(seconds)


class FeishuClient:
    """Authenticate and send messages as a Feishu application bot."""

    retry_statuses: ClassVar[set[int]] = {429, 500, 502, 503, 504}

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        receive_id: str | None,
        config: FeishuConfig,
        *,
        client: httpx.Client | None = None,
        sleeper: Sleeper | None = None,
        parser: FeishuResponseParser | None = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if not re.fullmatch(r"cli_[A-Za-z0-9]{8,}", app_id):
            raise FeishuAuthenticationError("飞书 App ID 格式无效。")
        if not app_secret.strip():
            raise FeishuAuthenticationError("飞书 App Secret 未配置。")
        self.app_id = app_id
        self.app_secret = app_secret
        self.receive_id = receive_id
        self.config = config
        self.client = client or httpx.Client(follow_redirects=False)
        self.sleeper = sleeper or SystemSleeper()
        self.parser = parser or FeishuResponseParser()
        self.clock = clock
        self._access_token: str | None = None
        self._access_token_expires_at = 0.0

    def authenticate(self) -> FeishuSendResponse:
        """Fetch and cache a tenant access token without sending a message."""
        self._tenant_access_token(force=True)
        return FeishuSendResponse(
            success=True,
            http_status=200,
            code=0,
            message="application authentication success",
        )

    def send_text(self, content: str) -> FeishuSendResponse:
        return self.send_payload({"msg_type": "text", "content": {"text": content}})

    def send_card(self, card: dict[str, object]) -> FeishuSendResponse:
        return self.send_payload({"msg_type": "interactive", "card": card})

    def send_payload(self, payload: dict[str, object]) -> FeishuSendResponse:
        if not self.receive_id:
            raise FeishuRequestError("未配置飞书应用机器人的消息接收目标。")
        body = self._message_body(payload)
        self._validate_payload_size(body)
        response = self._post_message(body, token=self._tenant_access_token())
        if response.status_code in {401, 403}:
            response = self._post_message(
                body, token=self._tenant_access_token(force=True)
            )
        return self._parse_message_response(response)

    def test_connection(self, *, send_message: bool = False) -> FeishuSendResponse:
        if not send_message:
            return self.authenticate()
        return self.send_text("gitplus 飞书应用机器人连接测试")

    def _tenant_access_token(self, *, force: bool = False) -> str:
        if (
            not force
            and self._access_token
            and self.clock() < self._access_token_expires_at
        ):
            return self._access_token
        response = self._post_with_retry(
            self.config.api_base_url.rstrip("/")
            + "/open-apis/auth/v3/tenant_access_token/internal/",
            json_body={"app_id": self.app_id, "app_secret": self.app_secret},
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": f"gitplus/{__version__}",
            },
        )
        try:
            data = response.json()
        except ValueError as exc:
            raise FeishuResponseError("飞书应用鉴权响应不是合法 JSON。") from exc
        if not isinstance(data, dict):
            raise FeishuResponseError("飞书应用鉴权响应结构异常。")
        code = data.get("code")
        token = data.get("tenant_access_token")
        expire = data.get("expire", 0)
        if response.status_code in {401, 403} or code not in {0, "0"}:
            raise FeishuAuthenticationError("飞书 App ID 或 App Secret 鉴权失败。")
        if not isinstance(token, str) or not token:
            raise FeishuResponseError("飞书应用鉴权响应缺少 tenant_access_token。")
        self._access_token = token
        self._access_token_expires_at = self.clock() + max(int(expire) - 60, 0)
        return token

    def _message_body(self, payload: dict[str, object]) -> dict[str, object]:
        message_type = payload.get("msg_type")
        if message_type == "text":
            content = payload.get("content")
        elif message_type == "interactive":
            content = payload.get("card")
        else:
            raise FeishuRequestError("飞书应用机器人仅支持 text 或 interactive 消息。")
        if not isinstance(content, dict):
            raise FeishuRequestError("飞书消息内容结构无效。")
        return {
            "receive_id": self.receive_id,
            "msg_type": message_type,
            "content": json.dumps(content, ensure_ascii=False, separators=(",", ":")),
        }

    def _post_with_retry(
        self,
        url: str,
        *,
        json_body: dict[str, object],
        headers: dict[str, str],
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        attempts = self.config.max_retries + 1
        for attempt in range(attempts):
            try:
                response = self.client.post(
                    url,
                    params=params,
                    json=json_body,
                    headers=headers,
                    timeout=self.config.request_timeout_seconds,
                )
            except httpx.TimeoutException as exc:
                if attempt >= attempts - 1:
                    raise FeishuTimeoutError("飞书应用 API 请求超时。") from exc
                self.sleeper.sleep(self.config.retry_backoff_seconds * (2**attempt))
                continue
            except httpx.TransportError as exc:
                if attempt >= attempts - 1:
                    raise FeishuConnectionError("飞书应用 API 连接失败。") from exc
                self.sleeper.sleep(self.config.retry_backoff_seconds * (2**attempt))
                continue
            if 300 <= response.status_code < 400:
                raise FeishuConnectionError("飞书应用 API 返回重定向，已阻止。")
            if response.status_code in self.retry_statuses and attempt < attempts - 1:
                self.sleeper.sleep(self.config.retry_backoff_seconds * (2**attempt))
                continue
            if response.status_code == 429:
                raise FeishuRateLimitError("飞书应用 API 请求频率受限。")
            if response.status_code >= 500:
                raise FeishuConnectionError(
                    f"飞书应用 API 暂不可用：HTTP {response.status_code}"
                )
            return response
        raise FeishuConnectionError("飞书应用 API 请求失败。")

    def _post_message(
        self, body: dict[str, object], *, token: str
    ) -> httpx.Response:
        return self._post_with_retry(
            self.config.api_base_url.rstrip("/") + "/open-apis/im/v1/messages",
            json_body=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": f"gitplus/{__version__}",
            },
            params={"receive_id_type": self.config.receive_id_type},
        )

    def _validate_payload_size(self, payload: dict[str, object]) -> None:
        byte_size = len(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
        )
        if byte_size > self.config.max_json_bytes:
            raise NotificationContentTooLargeError("飞书消息超过配置的 JSON 字节上限。")

    def _parse_message_response(self, response: httpx.Response) -> FeishuSendResponse:
        try:
            data = response.json()
        except ValueError as exc:
            raise FeishuResponseError("飞书消息响应不是合法 JSON。") from exc
        if not isinstance(data, dict):
            raise FeishuResponseError("飞书消息响应结构异常。")
        result = self.parser.parse(
            http_status=response.status_code,
            data=data,
            headers=dict(response.headers),
        )
        if result.success:
            return result
        if response.status_code in {401, 403}:
            raise FeishuAuthenticationError("飞书应用访问凭证无效或权限不足。")
        detail = str(result.code or response.status_code)
        if result.message:
            detail = f"{detail} ({result.message})"
        if result.request_id:
            detail = f"{detail}; request_id={result.request_id}"
        raise FeishuRequestError(f"飞书应用机器人拒绝消息请求：{detail}")


class FeishuWebhookClient:
    """Send messages through a Feishu custom webhook bot."""

    def __init__(
        self,
        webhook: str,
        config: FeishuConfig,
        *,
        secret: str | None = None,
        client: httpx.Client | None = None,
        parser: FeishuResponseParser | None = None,
    ) -> None:
        if not webhook.strip():
            raise FeishuAuthenticationError("飞书 Webhook 未配置。")
        self.webhook = webhook
        self.secret = secret
        self.config = config
        self.client = client or httpx.Client(follow_redirects=False)
        self.parser = parser or FeishuResponseParser()

    def test_connection(self, *, send_message: bool = False) -> FeishuSendResponse:
        if not send_message:
            return FeishuSendResponse(
                success=True, http_status=200, code=0, message="webhook configured"
            )
        return self.send_payload(
            {"msg_type": "text", "content": {"text": "gitplus 飞书 Webhook 连接测试"}}
        )

    def send_payload(self, payload: dict[str, object]) -> FeishuSendResponse:
        body = dict(payload)
        body.update(self._signature_fields())
        byte_size = len(
            json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        )
        if byte_size > self.config.max_json_bytes:
            raise NotificationContentTooLargeError("飞书消息超过配置的 JSON 字节上限。")
        try:
            response = self.client.post(
                self.webhook,
                json=body,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "User-Agent": f"gitplus/{__version__}",
                },
                timeout=self.config.request_timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise FeishuTimeoutError("飞书 Webhook 请求超时。") from exc
        except httpx.TransportError as exc:
            raise FeishuConnectionError("飞书 Webhook 连接失败。") from exc
        if 300 <= response.status_code < 400:
            raise FeishuConnectionError("飞书 Webhook 返回重定向，已阻止。")
        try:
            data = response.json()
        except ValueError as exc:
            raise FeishuResponseError("飞书 Webhook 响应不是合法 JSON。") from exc
        if not isinstance(data, dict):
            raise FeishuResponseError("飞书 Webhook 响应结构异常。")
        parsed = self.parser.parse(
            http_status=response.status_code,
            data=data,
            headers=dict(response.headers),
        )
        if parsed.success:
            return parsed
        raise FeishuRequestError(
            f"飞书 Webhook 拒绝消息请求：{parsed.code or response.status_code}"
        )

    def _signature_fields(self) -> dict[str, object]:
        if not self.secret:
            return {}
        timestamp = str(int(time()))
        key = f"{timestamp}\n{self.secret}".encode()
        digest = hmac.new(key, b"", digestmod=hashlib.sha256).digest()
        return {
            "timestamp": timestamp,
            "sign": base64.b64encode(digest).decode("ascii"),
        }

"""Feishu custom bot HTTP client."""

from __future__ import annotations

import ipaddress
import json
from time import sleep
from typing import ClassVar, Protocol
from urllib.parse import urlparse

import httpx

from gitpulse import __version__
from gitpulse.config import FeishuConfig
from gitpulse.exceptions import (
    FeishuAuthenticationError,
    FeishuConnectionError,
    FeishuRequestError,
    FeishuResponseError,
    FeishuTimeoutError,
    FeishuWebhookError,
    NotificationContentTooLargeError,
)
from gitpulse.integrations.feishu_response import FeishuResponseParser
from gitpulse.integrations.feishu_signer import FeishuSigner
from gitpulse.models.feishu import FeishuSendResponse


class Sleeper(Protocol):
    def sleep(self, seconds: float) -> None:
        """Sleep for retry backoff."""


class SystemSleeper:
    def sleep(self, seconds: float) -> None:
        sleep(seconds)


class FeishuWebhookValidator:
    """Validate Feishu webhook URLs without leaking credentials."""

    allowed_hosts: ClassVar[set[str]] = {"open.feishu.cn", "open.larksuite.com"}

    def validate(self, webhook: str) -> None:
        parsed = urlparse(webhook)
        if parsed.scheme != "https":
            raise FeishuWebhookError("飞书 Webhook 必须使用 HTTPS。")
        if parsed.username or parsed.password:
            raise FeishuWebhookError("飞书 Webhook 不能包含用户名或密码。")
        if parsed.fragment:
            raise FeishuWebhookError("飞书 Webhook 不能包含 URL Fragment。")
        host = parsed.hostname or ""
        if host not in self.allowed_hosts:
            raise FeishuWebhookError("飞书 Webhook 域名不在允许列表中。")
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            ip = None
        if ip and (ip.is_private or ip.is_loopback or ip.is_link_local):
            raise FeishuWebhookError("飞书 Webhook 不能指向内网或本机地址。")
        if not parsed.path.startswith("/open-apis/bot/v2/hook/"):
            raise FeishuWebhookError("飞书 Webhook 路径不是自定义机器人 v2 地址。")

    def mask(self, webhook: str) -> str:
        parsed = urlparse(webhook)
        token = parsed.path.rsplit("/", 1)[-1]
        suffix = token[-4:] if token else "****"
        return f"{parsed.scheme}://{parsed.netloc}/open-apis/bot/v2/hook/****{suffix}"


class FeishuClient:
    """Send text and interactive messages to a Feishu custom bot."""

    retry_statuses: ClassVar[set[int]] = {429, 500, 502, 503, 504}

    def __init__(
        self,
        webhook: str,
        config: FeishuConfig,
        *,
        signer: FeishuSigner | None = None,
        client: httpx.Client | None = None,
        sleeper: Sleeper | None = None,
        validator: FeishuWebhookValidator | None = None,
        parser: FeishuResponseParser | None = None,
    ) -> None:
        self.webhook = webhook
        self.config = config
        self.signer = signer
        self.client = client or httpx.Client(follow_redirects=False)
        self.sleeper = sleeper or SystemSleeper()
        self.validator = validator or FeishuWebhookValidator()
        self.parser = parser or FeishuResponseParser()
        self.validator.validate(webhook)

    def send_text(self, content: str) -> FeishuSendResponse:
        return self.send_payload({"msg_type": "text", "content": {"text": content}})

    def send_card(self, card: dict[str, object]) -> FeishuSendResponse:
        return self.send_payload({"msg_type": "interactive", "card": card})

    def send_payload(self, payload: dict[str, object]) -> FeishuSendResponse:
        attempts = self.config.max_retries + 1
        last_timeout: FeishuTimeoutError | None = None
        for attempt in range(attempts):
            signed_payload = self._with_signature(payload)
            self._validate_payload_size(signed_payload)
            try:
                response = self.client.post(
                    self.webhook,
                    json=signed_payload,
                    headers={
                        "Content-Type": "application/json; charset=utf-8",
                        "User-Agent": f"GitPulse/{__version__}",
                    },
                    timeout=self.config.request_timeout_seconds,
                )
            except httpx.TimeoutException as exc:
                last_timeout = FeishuTimeoutError("飞书请求超时，发送结果未知。")
                if attempt >= attempts - 1:
                    raise last_timeout from exc
                self.sleeper.sleep(self.config.retry_backoff_seconds * (2**attempt))
                continue
            except httpx.TransportError as exc:
                if attempt >= attempts - 1:
                    raise FeishuConnectionError("飞书连接失败。") from exc
                self.sleeper.sleep(self.config.retry_backoff_seconds * (2**attempt))
                continue
            if 300 <= response.status_code < 400:
                raise FeishuWebhookError("飞书 Webhook 返回重定向，已阻止。")
            if response.status_code in self.retry_statuses and attempt < attempts - 1:
                self.sleeper.sleep(self.config.retry_backoff_seconds * (2**attempt))
                continue
            return self._parse_response(response)
        if last_timeout:
            raise last_timeout
        raise FeishuConnectionError("飞书发送失败。")

    def test_connection(self) -> FeishuSendResponse:
        return self.send_text("GitPulse 飞书机器人连接测试")

    def _with_signature(self, payload: dict[str, object]) -> dict[str, object]:
        result = dict(payload)
        if self.signer:
            signature = self.signer.generate()
            result["timestamp"] = signature.timestamp
            result["sign"] = signature.sign
        return result

    def _validate_payload_size(self, payload: dict[str, object]) -> None:
        byte_size = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        if byte_size > self.config.max_json_bytes:
            raise NotificationContentTooLargeError("飞书消息超过配置的 JSON 字节上限。")

    def _parse_response(self, response: httpx.Response) -> FeishuSendResponse:
        try:
            data = response.json()
        except ValueError as exc:
            raise FeishuResponseError("飞书响应不是合法 JSON。") from exc
        if not isinstance(data, dict):
            raise FeishuResponseError("飞书响应结构异常。")
        result = self.parser.parse(http_status=response.status_code, data=data, headers=dict(response.headers))
        if result.success:
            return result
        if result.code in {19021, "19021"}:
            raise FeishuAuthenticationError("飞书签名校验失败。")
        if response.status_code in {400, 401, 403}:
            raise FeishuRequestError(f"飞书拒绝请求：{result.code or response.status_code}")
        return result

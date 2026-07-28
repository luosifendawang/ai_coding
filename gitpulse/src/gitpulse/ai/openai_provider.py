"""OpenAI-compatible chat completions provider."""

from __future__ import annotations

import os
import time
from urllib.parse import urlparse

import httpx

from gitpulse.ai.provider import LLMProvider
from gitpulse.config import AIConfig, load_config
from gitpulse.exceptions import (
    AIAuthenticationError,
    AIConfigurationError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)
from gitpulse.models.ai import AIRequest, AIResponse


class OpenAICompatibleProvider(LLMProvider):
    """Call an OpenAI-compatible `/chat/completions` endpoint."""

    name = "openai-compatible"

    def __init__(
        self,
        config: AIConfig | None = None,
        client: httpx.Client | None = None,
        sleeper: callable | None = None,
    ) -> None:
        self.config = config or load_config().ai
        self.client = client or httpx.Client(timeout=self.config.timeout_seconds)
        self.sleeper = sleeper or time.sleep

    @property
    def is_local(self) -> bool:
        if self.config.is_local is not None:
            return self.config.is_local
        host = urlparse(self.config.base_url).hostname or ""
        return host in {"localhost", "127.0.0.1", "::1"}

    def generate(self, request: AIRequest) -> AIResponse:
        api_key = self.config.api_key or os.getenv(self.config.api_key_env)
        if not api_key and not self.is_local:
            raise AIConfigurationError(
                f"未找到 AI API Key，请在 .gitpulse.yml 配置 ai.api_key 或设置环境变量：{self.config.api_key_env}"
            )

        payload = {
            "model": request.model,
            "messages": [message.model_dump() for message in request.messages],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "max_tokens": request.max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = "Bearer ***"
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                start = time.perf_counter()
                request_headers = dict(headers)
                if api_key:
                    request_headers["Authorization"] = f"Bearer {api_key}"
                response = self.client.post(url, json=payload, headers=request_headers)
                latency_ms = int((time.perf_counter() - start) * 1000)
                self._raise_for_status(response)
                data = response.json()
                choice = (data.get("choices") or [{}])[0]
                message = choice.get("message") or {}
                content = self._extract_message_content(message)
                if not content:
                    finish_reason = choice.get("finish_reason") or "unknown"
                    message_keys = ", ".join(sorted(message)) if isinstance(message, dict) else type(message).__name__
                    raise AIProviderError(
                        "AI Provider 返回空响应："
                        f"finish_reason={finish_reason}，message_keys={message_keys or 'empty'}。"
                    )
                usage = data.get("usage") or {}
                return AIResponse(
                    content=content,
                    model=data.get("model"),
                    request_id=response.headers.get("x-request-id"),
                    finish_reason=choice.get("finish_reason"),
                    input_tokens=usage.get("prompt_tokens"),
                    output_tokens=usage.get("completion_tokens"),
                    latency_ms=latency_ms,
                )
            except (httpx.TimeoutException, TimeoutError) as exc:
                last_error = AITimeoutError("AI Provider 请求超时。")
            except (httpx.ConnectError, httpx.NetworkError, AIRateLimitError) as exc:
                last_error = exc if isinstance(exc, AIRateLimitError) else AIProviderError("AI Provider 网络请求失败。")
            except AIProviderError as exc:
                if not self._is_retryable_error(exc):
                    raise exc
                last_error = exc
            if attempt < self.config.max_retries:
                self.sleeper(0.5 * (attempt + 1))
        if isinstance(last_error, AIProviderError):
            raise last_error
        raise AIProviderError("AI Provider 请求失败。")

    def health_check(self) -> bool:
        return True

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        if response.status_code in {401, 403}:
            raise AIAuthenticationError(f"AI Provider 鉴权失败：HTTP {response.status_code}")
        if response.status_code == 429:
            raise AIRateLimitError("AI Provider 请求频率受限。")
        if response.status_code >= 500:
            raise AIProviderError(f"AI Provider 服务暂不可用：HTTP {response.status_code}")
        raise AIProviderError(f"AI Provider 请求失败：HTTP {response.status_code}")

    def _is_retryable_error(self, exc: AIProviderError) -> bool:
        return isinstance(exc, AIRateLimitError) or "暂不可用" in str(exc) or "网络" in str(exc)

    def _extract_message_content(self, message: object) -> str:
        if not isinstance(message, dict):
            return ""
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("content"), str):
                    parts.append(item["content"])
            return "".join(parts).strip()
        return ""

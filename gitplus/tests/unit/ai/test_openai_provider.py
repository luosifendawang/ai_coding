from __future__ import annotations

import httpx
import pytest

from gitplus.ai.openai_provider import OpenAICompatibleProvider
from gitplus.config import AIConfig
from gitplus.exceptions import (
    AIAuthenticationError,
    AIConfigurationError,
    AIProviderError,
    AIRateLimitError,
)
from gitplus.models.ai import AIMessage, AIRequest


def request() -> AIRequest:
    return AIRequest(
        messages=[AIMessage(role="user", content="Generate JSON")],
        model="test-model",
        temperature=0.2,
        top_p=0.8,
        max_output_tokens=100,
    )


def client_for(status_code: int, body: dict | str) -> httpx.Client:
    def handler(_request: httpx.Request) -> httpx.Response:
        if isinstance(body, dict):
            return httpx.Response(status_code, json=body)
        return httpx.Response(status_code, text=body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_openai_provider_uses_configured_api_key_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITPLUS_API_KEY", raising=False)
    seen_headers = {}

    def handler(request_: httpx.Request) -> httpx.Response:
        seen_headers["authorization"] = request_.headers.get("Authorization")
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"ok": true}'}}]})

    provider = OpenAICompatibleProvider(
        AIConfig(base_url="https://example.test/v1", api_key="test-configured-key", is_local=False),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert provider.generate(request()).content == '{"ok": true}'
    assert seen_headers["authorization"] == "Bearer test-configured-key"


def test_openai_provider_generates_response_from_mock_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITPLUS_API_KEY", "test-key")
    provider = OpenAICompatibleProvider(
        AIConfig(base_url="https://example.test/v1", is_local=False),
        client=client_for(
            200,
            {
                "model": "test-model",
                "choices": [{"message": {"content": '{"ok": true}'}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 4},
            },
        ),
    )

    response = provider.generate(request())

    assert response.content == '{"ok": true}'
    assert response.input_tokens == 3
    assert provider.is_local is False


def test_openai_provider_accepts_content_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITPLUS_API_KEY", "test-key")
    provider = OpenAICompatibleProvider(
        AIConfig(base_url="https://example.test/v1", is_local=False),
        client=client_for(
            200,
            {"choices": [{"message": {"content": [{"type": "text", "text": '{"ok": true}'}]}}]},
        ),
    )

    assert provider.generate(request()).content == '{"ok": true}'


def test_openai_provider_empty_content_error_includes_response_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITPLUS_API_KEY", "test-key")
    provider = OpenAICompatibleProvider(
        AIConfig(base_url="https://example.test/v1", is_local=False, max_retries=0),
        client=client_for(200, {"choices": [{"message": {"content": ""}, "finish_reason": "length"}]}),
    )

    with pytest.raises(AIProviderError, match="finish_reason=length"):
        provider.generate(request())


def test_openai_provider_defaults_to_project_config(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".gitplus.yml").write_text(
        """
ai:
  base_url: https://configured.example.test/v1
  model: configured-model
  api_key_env: CONFIGURED_API_KEY
  is_local: false
""",
        encoding="utf-8",
    )

    provider = OpenAICompatibleProvider(client=client_for(200, {"choices": [{"message": {"content": '{"ok": true}'}}]}))

    assert provider.config.base_url == "https://configured.example.test/v1"
    assert provider.config.model == "configured-model"
    assert provider.config.api_key_env == "CONFIGURED_API_KEY"
    assert provider.is_local is False


def test_openai_provider_allows_local_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITPLUS_API_KEY", raising=False)
    provider = OpenAICompatibleProvider(
        AIConfig(base_url="http://localhost:11434/v1"),
        client=client_for(200, {"choices": [{"message": {"content": '{"ok": true}'}}]}),
    )

    assert provider.generate(request()).content == '{"ok": true}'
    assert provider.is_local is True


def test_openai_provider_requires_api_key_for_remote(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITPLUS_API_KEY", raising=False)
    provider = OpenAICompatibleProvider(
        AIConfig(base_url="https://example.test/v1", is_local=False),
        client=client_for(200, {}),
    )

    with pytest.raises(AIConfigurationError):
        provider.generate(request())


@pytest.mark.parametrize(
    ("status", "error_type"),
    [(401, AIAuthenticationError), (403, AIAuthenticationError), (429, AIRateLimitError), (500, AIProviderError)],
)
def test_openai_provider_maps_http_errors(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    error_type: type[Exception],
) -> None:
    monkeypatch.setenv("GITPLUS_API_KEY", "test-key")
    provider = OpenAICompatibleProvider(
        AIConfig(base_url="https://example.test/v1", is_local=False, max_retries=0),
        client=client_for(status, {"error": {"message": "bad"}}),
    )

    with pytest.raises(error_type):
        provider.generate(request())

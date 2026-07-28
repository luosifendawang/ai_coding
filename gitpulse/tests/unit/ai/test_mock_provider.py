from gitpulse.ai.mock_provider import MockLLMProvider
from gitpulse.exceptions import AIProviderError
from gitpulse.models.ai import AIMessage, AIRequest


def request() -> AIRequest:
    return AIRequest(
        messages=[AIMessage(role="user", content="hello")],
        model="mock",
        temperature=0.2,
        top_p=0.8,
        max_output_tokens=100,
    )


def test_mock_provider_returns_predefined_responses() -> None:
    provider = MockLLMProvider(responses=['{"ok": 1}', '{"ok": 2}'])

    first = provider.generate(request())
    second = provider.generate(request())

    assert first.content == '{"ok": 1}'
    assert second.content == '{"ok": 2}'
    assert provider.call_count == 2
    assert provider.requests[0].messages[0].content == "hello"
    assert provider.is_local is True


def test_mock_provider_can_raise_error() -> None:
    provider = MockLLMProvider(raise_error=AIProviderError("boom"))

    try:
        provider.generate(request())
    except AIProviderError as exc:
        assert "boom" in str(exc)
    else:
        raise AssertionError("expected AIProviderError")


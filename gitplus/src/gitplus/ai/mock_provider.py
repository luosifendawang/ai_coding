"""Mock LLM provider for tests and offline demos."""

from __future__ import annotations

from gitplus.ai.provider import LLMProvider
from gitplus.exceptions import AIProviderError
from gitplus.models.ai import AIRequest, AIResponse

DEFAULT_MOCK_COMMIT_RESPONSE = """
{
  "primary_purpose": "根据暂存变更生成提交说明",
  "type": "chore",
  "scope": null,
  "subject": "chore: 更新项目变更",
  "body": ["整理当前暂存区中的项目修改"],
  "confidence": "medium",
  "candidates": {
    "concise": {"subject": "chore: 更新项目变更", "body": []},
    "standard": {"subject": "chore: 更新项目变更", "body": ["整理当前暂存区中的项目修改"]},
    "detailed": {"subject": "chore: 更新项目变更", "body": ["整理当前暂存区中的项目修改", "保留生成依据供用户确认"]}
  },
  "should_split": false,
  "split_confidence": 0.0,
  "split_suggestions": [],
  "evidence": [],
  "needs_confirmation": ["请确认提交类型和主要目的是否准确"]
}
"""


class MockLLMProvider(LLMProvider):
    """Return predefined responses and record requests."""

    name = "mock"

    def __init__(
        self,
        responses: list[str] | None = None,
        *,
        raise_error: Exception | None = None,
    ) -> None:
        self.responses = responses or [DEFAULT_MOCK_COMMIT_RESPONSE]
        self.raise_error = raise_error
        self.call_count = 0
        self.requests: list[AIRequest] = []

    @property
    def is_local(self) -> bool:
        return True

    def generate(self, request: AIRequest) -> AIResponse:
        self.call_count += 1
        self.requests.append(request)
        if self.raise_error:
            raise self.raise_error
        if not self.responses:
            raise AIProviderError("Mock Provider 没有可用响应。")
        index = min(self.call_count - 1, len(self.responses) - 1)
        return AIResponse(content=self.responses[index], model=request.model, finish_reason="stop")

    def health_check(self) -> bool:
        return self.raise_error is None


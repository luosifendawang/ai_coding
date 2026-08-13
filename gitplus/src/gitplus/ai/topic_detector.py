"""Topic detection orchestration."""

from __future__ import annotations

import json

from gitplus.ai.prompt_loader import PromptLoader
from gitplus.ai.provider import LLMProvider
from gitplus.ai.response_parser import AIResponseParser
from gitplus.exceptions import TopicDetectionError
from gitplus.models.ai import AIMessage, AIRequest
from gitplus.models.commit import CommitAIRequest, TopicDetectionResult


class TopicDetector:
    """Detect whether a diff contains multiple independent commit topics."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        model: str = "local-model",
        temperature: float = 0.2,
        top_p: float = 0.8,
        parser: AIResponseParser | None = None,
        prompt_loader: PromptLoader | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.parser = parser or AIResponseParser()
        self.prompt_loader = prompt_loader or PromptLoader()

    def detect(self, request: CommitAIRequest) -> TopicDetectionResult:
        system = self.prompt_loader.load("topic_system.txt")
        user = self.prompt_loader.render(
            "topic_user.txt",
            {
                "repository": request.repository,
                "branch": request.branch or "",
                "user_context": request.user_context or "",
                "files_json": json.dumps([file.model_dump() for file in request.files], ensure_ascii=False),
                "sanitized_diff": request.sanitized_diff,
            },
        )
        ai_request = AIRequest(
            messages=[AIMessage(role="system", content=system), AIMessage(role="user", content=user)],
            model=self.model,
            temperature=self.temperature,
            top_p=self.top_p,
            max_output_tokens=2000,
            response_schema=TopicDetectionResult.model_json_schema(),
        )
        response = self.provider.generate(ai_request)
        result = self.parser.parse(response.content, TopicDetectionResult)
        valid_files = {file.path for file in request.files}
        invalid = [
            file
            for topic in result.topics
            for file in topic.files
            if file not in valid_files
        ]
        invalid.extend(file for file in result.ambiguous_files if file not in valid_files)
        if invalid:
            raise TopicDetectionError(f"主题检测结果引用了不存在的文件：{', '.join(sorted(set(invalid)))}")
        return result

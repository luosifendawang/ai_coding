"""Commit message generation orchestration."""

from __future__ import annotations

import json

from gitpulse.ai.commit_validator import CommitMessageValidator
from gitpulse.ai.prompt_loader import PromptLoader
from gitpulse.ai.provider import LLMProvider
from gitpulse.ai.response_parser import AIResponseParser
from gitpulse.models.ai import AIMessage, AIRequest
from gitpulse.models.commit import CommitAIRequest, CommitGenerationResult


class CommitGenerator:
    """Build commit prompts, call a provider, and validate structured output."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        model: str = "local-model",
        temperature: float = 0.2,
        top_p: float = 0.8,
        max_output_tokens: int = 3000,
        parser: AIResponseParser | None = None,
        prompt_loader: PromptLoader | None = None,
        validator: CommitMessageValidator | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.max_output_tokens = max_output_tokens
        self.parser = parser or AIResponseParser()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.validator = validator or CommitMessageValidator()

    def generate(self, request: CommitAIRequest) -> CommitGenerationResult:
        system = self.prompt_loader.load("commit_system.txt")
        user = self.prompt_loader.render("commit_user.txt", self._variables(request))
        ai_request = AIRequest(
            messages=[AIMessage(role="system", content=system), AIMessage(role="user", content=user)],
            model=self.model,
            temperature=self.temperature,
            top_p=self.top_p,
            max_output_tokens=self.max_output_tokens,
            response_schema=CommitGenerationResult.model_json_schema(),
        )
        response = self.provider.generate(ai_request)
        result = self.parser.parse(response.content, CommitGenerationResult)
        valid_files = {file.path for file in request.files}
        validation_warnings = self.validator.validate_result(result, request.commit_rules, valid_files=valid_files)
        result.validation_warnings = list(dict.fromkeys([*result.validation_warnings, *validation_warnings]))
        return result

    def _variables(self, request: CommitAIRequest) -> dict[str, str]:
        return {
            "repository": request.repository,
            "branch": request.branch or "",
            "head_commit": request.head_commit or "",
            "user_context": request.user_context or "",
            "commit_rules_json": request.commit_rules.model_dump_json(),
            "stats_json": json.dumps(request.stats, ensure_ascii=False),
            "files_json": json.dumps([file.model_dump() for file in request.files], ensure_ascii=False),
            "security_warnings_json": json.dumps(request.security_warnings, ensure_ascii=False),
            "sanitized_diff": request.sanitized_diff,
        }

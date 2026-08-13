"""AI weekly report generation orchestration."""

from __future__ import annotations

import json

from gitplus.ai.prompt_loader import PromptLoader
from gitplus.ai.provider import LLMProvider
from gitplus.ai.response_parser import AIResponseParser
from gitplus.models.ai import AIMessage, AIRequest
from gitplus.models.weekly import WeeklyGenerationInput, WeeklyReportDraft
from gitplus.weekly.fact_validator import WeeklyFactValidator


class WeeklyGenerator:
    """Build weekly prompts, call a provider, and validate the draft facts."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        model: str = "local-model",
        temperature: float = 0.2,
        top_p: float = 0.8,
        max_output_tokens: int = 4000,
        parser: AIResponseParser | None = None,
        prompt_loader: PromptLoader | None = None,
        validator: WeeklyFactValidator | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.max_output_tokens = max_output_tokens
        self.parser = parser or AIResponseParser()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.validator = validator or WeeklyFactValidator()

    def generate(self, generation_input: WeeklyGenerationInput) -> WeeklyReportDraft:
        system = self.prompt_loader.load("weekly_system.txt")
        user = self.prompt_loader.render(
            "weekly_user.txt",
            {
                "input_json": json.dumps(generation_input.model_dump(mode="json"), ensure_ascii=False),
                "schema_json": json.dumps(WeeklyReportDraft.model_json_schema(), ensure_ascii=False),
            },
        )
        request = AIRequest(
            messages=[AIMessage(role="system", content=system), AIMessage(role="user", content=user)],
            model=self.model,
            temperature=self.temperature,
            top_p=self.top_p,
            max_output_tokens=self.max_output_tokens,
            response_schema=WeeklyReportDraft.model_json_schema(),
        )
        response = self.provider.generate(request)
        draft = self.parser.parse(response.content, WeeklyReportDraft)
        validation = self.validator.validate(draft, generation_input)
        draft.source_coverage = validation.source_coverage
        return draft

import json
from pathlib import Path

from gitpulse.ai.mock_provider import MockLLMProvider
from gitpulse.ai.weekly_fallback import RuleBasedWeeklyGenerator
from gitpulse.ai.weekly_generator import WeeklyGenerator
from gitpulse.exceptions import AIResponseValidationError, AITimeoutError
from gitpulse.services.weekly_service import WeeklyService
from gitpulse.storage.database import Database
from tests.unit.weekly.test_weekly_pipeline import generation_input


class RaisingGenerator:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def generate(self, _generation_input):  # type: ignore[no-untyped-def]
        raise self.error


def test_weekly_ai_uses_sanitized_input_and_structured_output(
    tmp_path: Path,
) -> None:
    source = generation_input()
    draft = RuleBasedWeeklyGenerator().generate(source)
    draft.generator = "ai"
    provider = MockLLMProvider(
        responses=[json.dumps(draft.model_dump(mode="json"), ensure_ascii=False)]
    )
    service = WeeklyService(
        Database(tmp_path / "test.db"),
        generator=WeeklyGenerator(provider),
    )

    outcome = service.generate_from_input(source, use_ai=True)

    assert outcome.report.generator == "ai"
    assert outcome.warnings == []
    request_text = provider.requests[0].messages[-1].content
    assert "test@example.com" not in request_text


def test_weekly_invalid_ai_json_falls_back_to_rules(tmp_path: Path) -> None:
    service = WeeklyService(
        Database(tmp_path / "test.db"),
        generator=RaisingGenerator(
            AIResponseValidationError("invalid weekly json")
        ),
    )

    outcome = service.generate_from_input(generation_input(), use_ai=True)

    assert outcome.report.generator == "rule_based"
    assert outcome.warnings == ["AI 整理失败，已自动回退到规则模式。"]


def test_weekly_ai_timeout_falls_back_to_rules(tmp_path: Path) -> None:
    service = WeeklyService(
        Database(tmp_path / "test.db"),
        generator=RaisingGenerator(AITimeoutError("timeout")),
    )

    outcome = service.generate_from_input(generation_input(), use_ai=True)

    assert outcome.report.generator == "rule_based"
    assert outcome.warnings == ["AI 整理失败，已自动回退到规则模式。"]

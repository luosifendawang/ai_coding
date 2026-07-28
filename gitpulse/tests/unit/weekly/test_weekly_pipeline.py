from datetime import date, datetime, time, timezone

from gitpulse.ai.weekly_fallback import RuleBasedWeeklyGenerator
from gitpulse.exporters import JsonWeeklyExporter, MarkdownWeeklyExporter, TextWeeklyExporter
from gitpulse.models.weekly import WeeklyCommitInput, WeeklyDateRange, WeeklyGenerationInput, WeeklyReport
from gitpulse.weekly.fact_validator import WeeklyFactValidator
from gitpulse.weekly.normalizer import WeeklyNormalizer


def weekly_range() -> WeeklyDateRange:
    return WeeklyDateRange(
        date_from=date(2026, 7, 27),
        date_to=date(2026, 8, 2),
        datetime_from=datetime.combine(date(2026, 7, 27), time.min, tzinfo=timezone.utc),
        datetime_to=datetime.combine(date(2026, 8, 2), time.max, tzinfo=timezone.utc),
        timezone="UTC",
        label="2026-07-27 至 2026-08-02",
    )


def generation_input() -> WeeklyGenerationInput:
    return WeeklyGenerationInput(
        date_range=weekly_range(),
        commits=[
            WeeklyCommitInput(
                commit_hash="abcdef123456",
                short_hash="abcdef12",
                repository_id="repo_1",
                repository_name="repo",
                branch="main",
                author_email="test@example.com",
                committed_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
                subject="feat(weekly): 实现周报生成",
                body="补充本地规则生成器",
                files=["src/gitpulse/weekly/service.py"],
            )
        ],
    )


def test_normalizer_binds_commit_source() -> None:
    items = WeeklyNormalizer().normalize(generation_input())

    assert items[0].title == "实现周报生成"
    assert items[0].scope == "weekly"
    assert items[0].sources[0].label == "commit:abcdef12"


def test_rule_based_generator_creates_sourced_draft() -> None:
    draft = RuleBasedWeeklyGenerator().generate(generation_input())
    validation = WeeklyFactValidator().validate(draft, generation_input())

    assert draft.completed
    assert draft.completed[0].items[0].sources[0].label == "commit:abcdef12"
    assert validation.status == "pass"
    assert validation.source_coverage == 1.0


def test_fact_validator_rejects_unsourced_items() -> None:
    draft = RuleBasedWeeklyGenerator().generate(generation_input())
    draft.completed[0].items[0].sources = []

    validation = WeeklyFactValidator().validate(draft, generation_input())

    assert validation.status == "fail"
    assert validation.blocked_item_ids == [draft.completed[0].items[0].id]


def test_weekly_exporters_render_sources() -> None:
    draft = RuleBasedWeeklyGenerator().generate(generation_input())
    now = datetime.now(timezone.utc)
    report = WeeklyReport(
        id=draft.id,
        title=draft.title,
        date_range=draft.date_range,
        completed=draft.completed,
        debugging=draft.debugging,
        testing=draft.testing,
        risks=draft.risks,
        next_week=draft.next_week,
        source_coverage=draft.source_coverage,
        status="draft",
        content_markdown="",
        generator=draft.generator,
        created_at=now,
        updated_at=now,
    )

    markdown = MarkdownWeeklyExporter().render(report)
    text = TextWeeklyExporter().render(report)
    json_text = JsonWeeklyExporter().render(report)

    assert "来源：commit:abcdef12" in markdown
    assert "本周完成" in text
    assert '"source_coverage": 1.0' in json_text

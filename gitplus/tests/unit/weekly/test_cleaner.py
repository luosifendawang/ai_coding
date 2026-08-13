from datetime import date, datetime, time, timezone

from gitplus.models.storage import CommitRecord
from gitplus.models.weekly import (
    WeeklyCommitInput,
    WeeklyDateRange,
    WeeklyGenerationInput,
    WeeklyWorklogInput,
)
from gitplus.weekly.cleaner import WeeklyDataCleaner


def date_range() -> WeeklyDateRange:
    return WeeklyDateRange(
        date_from=date(2026, 7, 27),
        date_to=date(2026, 8, 2),
        datetime_from=datetime.combine(
            date(2026, 7, 27), time.min, tzinfo=timezone.utc
        ),
        datetime_to=datetime.combine(
            date(2026, 8, 2), time.max, tzinfo=timezone.utc
        ),
        timezone="UTC",
        label="本周",
    )


def test_cleaner_filters_templates_and_low_information() -> None:
    generation_input = WeeklyGenerationInput(
        date_range=date_range(),
        worklogs=[
            WeeklyWorklogInput(
                id="template",
                work_date=date(2026, 7, 28),
                work_type="other",
                title="Module: Brief and clear title",
            ),
            WeeklyWorklogInput(
                id="test",
                work_date=date(2026, 7, 28),
                work_type="test",
                title="test",
            ),
            WeeklyWorklogInput(
                id="valid",
                work_date=date(2026, 7, 28),
                work_type="development",
                title="完成周报编辑器",
                result="支持来源追踪",
            ),
        ],
    )

    result = WeeklyDataCleaner().clean(generation_input)

    assert [item.id for item in result.template_items] == [
        "worklog_template"
    ]
    assert [item.id for item in result.low_information_items] == [
        "worklog_test"
    ]
    assert [item.id for item in result.items] == ["worklog_valid"]


def test_cleaner_links_commit_record_and_removes_repeated_body() -> None:
    current = datetime(2026, 7, 28, tzinfo=timezone.utc)
    generation_input = WeeklyGenerationInput(
        date_range=date_range(),
        commits=[
            WeeklyCommitInput(
                commit_hash="abcdef1234567890",
                short_hash="abcdef12",
                repository_id="repo_1",
                repository_name="repo",
                author_email="test@example.com",
                committed_at=current,
                subject="feat(web): 增加周报页面",
                body="增加周报页面",
            )
        ],
        commit_records=[
            CommitRecord(
                id="record_1",
                repository_id="repo_1",
                commit_hash="abcdef1234567890",
                commit_type="feat",
                subject="feat(web): 增加周报页面",
                summary="增加周报页面",
                confirmed_by_user=True,
                created_at=current,
                updated_at=current,
            )
        ],
    )

    result = WeeklyDataCleaner().clean(generation_input)

    assert len(result.items) == 1
    assert result.items[0].description is None
    assert {source.source_type for source in result.items[0].sources} == {
        "commit",
        "record",
    }
    assert result.merged_groups[0].reason == "关联到相同 Commit，已合并来源"


def test_cleaner_does_not_merge_same_title_across_repositories() -> None:
    generation_input = WeeklyGenerationInput(
        date_range=date_range(),
        worklogs=[
            WeeklyWorklogInput(
                id="one",
                repository_id="repo_1",
                work_date=date(2026, 7, 28),
                work_type="development",
                title="更新配置",
            ),
            WeeklyWorklogInput(
                id="two",
                repository_id="repo_2",
                work_date=date(2026, 7, 28),
                work_type="development",
                title="更新配置",
            ),
        ],
    )

    result = WeeklyDataCleaner().clean(generation_input)

    assert len(result.items) == 2


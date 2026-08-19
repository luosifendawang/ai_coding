from __future__ import annotations

import json
from datetime import date
from typing import cast

import pytest

pytest.importorskip("sqlalchemy")

from gitplus.config import AIConfig
from gitplus.services.smart_weekly_service import SmartWeeklyService
from gitplus.storage.database import Database


def history_query(**_kwargs) -> dict[str, object]:
    return {
        "items": [
            {
                "id": "abc123",
                "record_type": "git_commit",
                "occurred_at": "2026-08-11T10:00:00+00:00",
                "title": "feat: 增加搜索",
                "summary": "实现仓库搜索",
                "repository": "gitplus",
                "commit_hash": "abc123",
            },
            {
                "id": "record-1",
                "record_type": "commit_record",
                "occurred_at": "2026-08-11T10:01:00+00:00",
                "title": "feat: 增加搜索",
                "summary": "实现仓库搜索并完成确认",
                "repository": "gitplus",
                "commit_hash": "abc123",
            },
            {
                "id": "worklog-1",
                "record_type": "worklog",
                "occurred_at": "2026-08-12T10:00:00+00:00",
                "title": "补充测试覆盖率",
                "summary": "增加服务单元测试",
                "repository": "gitplus",
                "commit_hash": None,
            },
        ],
        "total": 3,
    }


def service() -> SmartWeeklyService:
    return SmartWeeklyService(
        cast(Database, object()),
        history_query,
        lambda: (cast(object, object()), AIConfig()),  # type: ignore[arg-type,return-value]
        lambda: "repo-1",
    )


def test_sources_prefer_confirmed_record_over_raw_commit() -> None:
    items = service().sources(date(2026, 8, 10), date(2026, 8, 16))
    assert [item.id for item in items] == [
        "commit_record:record-1",
        "worklog:worklog-1",
    ]


def test_rule_generation_is_traceable_and_categorized() -> None:
    instance = service()
    sources = instance.sources(date(2026, 8, 10), date(2026, 8, 16))
    draft = instance.generate(
        date(2026, 8, 10),
        date(2026, 8, 16),
        [item.id for item in sources],
        use_ai=False,
        extra_context="下周准备发布",
    )
    assert draft.generator == "rule_based"
    assert draft.source_ids == [item.id for item in sources]
    assert "feat: 增加搜索" in draft.markdown
    assert "补充测试覆盖率" in draft.markdown
    assert "下周准备发布" in draft.markdown


def test_generation_rejects_empty_selection() -> None:
    with pytest.raises(ValueError, match="没有可用于生成"):
        service().generate(
            date(2026, 8, 10), date(2026, 8, 16), [], use_ai=False, extra_context=""
        )


def test_ai_parser_accepts_structured_items_and_collects_their_sources() -> None:
    source_id = "commit_record:record-1"
    content = json.dumps(
        {
            "title": "本周周报",
            "overview": "完成主要功能。",
            "sections": [
                {
                    "key": "completed",
                    "title": "本周完成",
                    "items": [{"description": "完成搜索功能", "source_id": source_id}],
                    "source_ids": [],
                },
                {
                    "key": "quality",
                    "title": "质量与改进",
                    "items": [],
                    "source_ids": [],
                },
                {"key": "risks", "title": "问题与风险", "items": [], "source_ids": []},
                {
                    "key": "next_week",
                    "title": "下周计划",
                    "items": [],
                    "source_ids": [],
                },
            ],
        },
        ensure_ascii=False,
    )

    draft = service()._parse_ai(
        content,
        date(2026, 8, 10),
        date(2026, 8, 16),
        [source_id],
        "mock",
    )

    assert draft.sections[0].items == ["完成搜索功能"]
    assert draft.sections[0].source_ids == [source_id]
    assert draft.generator == "mock"

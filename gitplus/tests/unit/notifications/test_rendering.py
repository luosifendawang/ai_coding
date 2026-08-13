from __future__ import annotations

from datetime import date, datetime, time, timezone

from gitplus.config import FeishuConfig
from gitplus.models.source import WeeklySourceReference
from gitplus.models.weekly import (
    WeeklyDateRange,
    WeeklyReport,
    WeeklyReportItem,
    WeeklyReportTopic,
)
from gitplus.notifications.fingerprint import NotificationFingerprint
from gitplus.notifications.renderer import FeishuNotificationRenderer
from gitplus.notifications.text_builder import FeishuTextBuilder


def report() -> WeeklyReport:
    now = datetime.now(timezone.utc)
    item = WeeklyReportItem(
        id="item_1",
        content="修复设备断开后的资源释放问题",
        confidence="high",
        confirmed_by_user=True,
        sources=[
            WeeklySourceReference(
                source_type="commit",
                source_id="abcdef123456",
                commit_hash="abcdef123456",
            )
        ],
    )
    return WeeklyReport(
        id="weekly_1",
        title="本周开发周报",
        date_range=WeeklyDateRange(
            date_from=date(2026, 7, 27),
            date_to=date(2026, 8, 2),
            datetime_from=datetime.combine(date(2026, 7, 27), time.min, timezone.utc),
            datetime_to=datetime.combine(date(2026, 8, 2), time.max, timezone.utc),
            timezone="UTC",
            label="本周",
        ),
        completed=[
            WeeklyReportTopic(
                id="topic_1",
                title="USB 设备异常断开处理",
                category="completed",
                confidence="high",
                confirmed_by_user=True,
                items=[item],
                sources=item.sources,
            )
        ],
        source_coverage=1,
        status="confirmed",
        content_markdown="# report",
        generator="rule_based",
        created_at=now,
        updated_at=now,
        confirmed_at=now,
    )


def test_text_builder_omits_sources_by_default() -> None:
    text = FeishuTextBuilder().build(report(), FeishuConfig())

    assert "gitplus 开发周报" in text
    assert "来源" not in text


def test_renderer_builds_interactive_payload_and_hash() -> None:
    payload = FeishuNotificationRenderer().render(
        report(), FeishuConfig(message_type="interactive")
    )

    assert payload.message_type == "interactive"
    assert payload.payload["msg_type"] == "interactive"
    assert len(payload.content_hash) == 64


def test_fingerprint_is_stable_for_the_same_application_message() -> None:
    fingerprint = NotificationFingerprint()
    one = fingerprint.generate(
        report_id="weekly_1",
        report_version=1,
        channel="feishu",
        message_type="text",
        normalized_payload={"msg_type": "text", "content": {"text": "hello"}},
    )
    two = fingerprint.generate(
        report_id="weekly_1",
        report_version=1,
        channel="feishu",
        message_type="text",
        normalized_payload={"msg_type": "text", "content": {"text": "hello"}},
    )

    assert one == two

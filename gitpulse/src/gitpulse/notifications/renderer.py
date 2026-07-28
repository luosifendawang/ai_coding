"""Notification payload rendering."""

from __future__ import annotations

from gitpulse.config import FeishuConfig
from gitpulse.models.notification import NotificationPayload
from gitpulse.models.weekly import WeeklyReport
from gitpulse.notifications.card_builder import FeishuWeeklyCardBuilder
from gitpulse.notifications.content_limiter import NotificationContentLimiter
from gitpulse.notifications.fingerprint import NotificationFingerprint
from gitpulse.notifications.text_builder import FeishuTextBuilder


class FeishuNotificationRenderer:
    """Render weekly reports into Feishu payloads."""

    def __init__(
        self,
        *,
        text_builder: FeishuTextBuilder | None = None,
        card_builder: FeishuWeeklyCardBuilder | None = None,
        limiter: NotificationContentLimiter | None = None,
        fingerprint: NotificationFingerprint | None = None,
    ) -> None:
        self.text_builder = text_builder or FeishuTextBuilder()
        self.card_builder = card_builder or FeishuWeeklyCardBuilder()
        self.limiter = limiter or NotificationContentLimiter()
        self.fingerprint = fingerprint or NotificationFingerprint()

    def render(self, report: WeeklyReport, config: FeishuConfig) -> NotificationPayload:
        text_preview = self.text_builder.build(report, config)
        if config.message_type == "text":
            raw_payload: dict[str, object] = {"msg_type": "text", "content": {"text": text_preview}}
        else:
            raw_payload = {"msg_type": "interactive", "card": self.card_builder.build(report, config)}
        payload, limited = self.limiter.limit_payload(report, raw_payload, max_json_bytes=config.max_json_bytes)
        content_hash = self.fingerprint.generate(
            report_id=report.id,
            report_version=report.version,
            channel="feishu",
            message_type=config.message_type,
            normalized_payload=payload,
        )
        return NotificationPayload(
            channel="feishu",
            message_type=config.message_type,
            title=report.title,
            text_preview=text_preview,
            payload=payload,
            content_hash=content_hash,
            byte_size=limited.final_bytes,
            truncated=limited.truncated,
            removed_sections=limited.removed_sections,
        )

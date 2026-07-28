"""Notification duplicate protection."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from gitpulse.models.notification import DuplicateCheckResult, NotificationPayload
from gitpulse.storage.database import Database
from gitpulse.storage.unit_of_work import UnitOfWork


class NotificationIdempotencyService:
    """Check recent sent or unknown notifications by content hash."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def check(
        self,
        payload: NotificationPayload,
        *,
        channel: str,
        window_hours: int,
    ) -> DuplicateCheckResult:
        since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        with UnitOfWork(self.database) as uow:
            records = uow.notifications.find_recent_by_hash(
                payload.content_hash,
                channel=channel,
                since=since,
                statuses=["sent", "unknown"],
            )
        if not records:
            return DuplicateCheckResult(is_duplicate=False)
        sent_records = [record for record in records if record.status == "sent"]
        last_sent = max((record.sent_at for record in sent_records if record.sent_at), default=None)
        return DuplicateCheckResult(
            is_duplicate=True,
            existing_notification_ids=[record.id for record in records],
            last_sent_at=last_sent,
            reason="检测到相同内容已发送或发送结果未知。",
        )

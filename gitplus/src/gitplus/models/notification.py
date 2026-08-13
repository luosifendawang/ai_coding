"""Notification domain models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

NotificationChannel = Literal["feishu"]
NotificationMessageType = Literal["text", "interactive"]
NotificationStatus = Literal[
    "pending",
    "previewed",
    "confirmed",
    "sending",
    "sent",
    "failed",
    "unknown",
    "cancelled",
    "duplicate_blocked",
]


class NotificationPayload(BaseModel):
    channel: NotificationChannel
    message_type: NotificationMessageType
    title: str
    text_preview: str
    payload: dict[str, object]
    content_hash: str
    byte_size: int
    truncated: bool = False
    removed_sections: list[str] = Field(default_factory=list)


class NotificationRecord(BaseModel):
    id: str
    report_id: str
    report_version: int = 1
    channel: NotificationChannel
    provider_mode: Literal["webhook", "app"] = "app"
    message_type: NotificationMessageType
    status: NotificationStatus
    content_hash: str
    target_digest: str | None = None
    feishu_message_id: str | None = None
    payload_summary: str | None = None
    byte_size: int = 0
    truncated: bool = False
    removed_sections: list[str] = Field(default_factory=list)
    attempt_count: int = 0
    http_status: int | None = None
    response_code: str | None = None
    response_message: str | None = None
    request_id: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    forced: bool = False
    sent_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DuplicateCheckResult(BaseModel):
    is_duplicate: bool
    existing_notification_ids: list[str] = Field(default_factory=list)
    last_sent_at: datetime | None = None
    reason: str | None = None


class EligibilityIssue(BaseModel):
    code: str
    message: str

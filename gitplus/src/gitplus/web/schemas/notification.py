"""Web request schemas for Feishu notifications."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class NotificationPreviewRequest(BaseModel):
    report_id: str = Field(min_length=1, max_length=120)
    message_type: Literal["text", "interactive"] = "interactive"


class NotificationTestRequest(BaseModel):
    confirmed: bool = False


class NotificationSendRequest(BaseModel):
    report_id: str = Field(min_length=1, max_length=120)
    message_type: Literal["text", "interactive"] = "interactive"
    confirmed: bool = False
    allow_duplicate: bool = False


class NotificationRetryRequest(BaseModel):
    confirmed: bool = False
    allow_duplicate: bool = False

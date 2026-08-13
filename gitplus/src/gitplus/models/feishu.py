"""Feishu request and response models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class FeishuTextContent(BaseModel):
    text: str


class FeishuTextMessage(BaseModel):
    msg_type: Literal["text"] = "text"
    content: FeishuTextContent


class FeishuCardHeaderTitle(BaseModel):
    tag: Literal["plain_text"] = "plain_text"
    content: str


class FeishuCardHeader(BaseModel):
    title: FeishuCardHeaderTitle
    template: str | None = None


class FeishuCardElement(BaseModel):
    tag: str
    text: dict[str, Any] | None = None
    fields: list[dict[str, Any]] | None = None
    actions: list[dict[str, Any]] | None = None


class FeishuCard(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)
    header: FeishuCardHeader
    elements: list[dict[str, Any]]


class FeishuInteractiveMessage(BaseModel):
    msg_type: Literal["interactive"] = "interactive"
    card: dict[str, Any]


class FeishuSendResponse(BaseModel):
    success: bool
    http_status: int | None = None
    code: int | str | None = None
    message: str | None = None
    request_id: str | None = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

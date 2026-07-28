"""Notification payload size limiting."""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from gitpulse.exceptions import NotificationContentTooLargeError
from gitpulse.models.weekly import WeeklyReport


class LimitedNotificationContent(BaseModel):
    report: WeeklyReport
    truncated: bool
    removed_sections: list[str] = Field(default_factory=list)
    original_bytes: int
    final_bytes: int
    warnings: list[str] = Field(default_factory=list)


class NotificationContentLimiter:
    """Apply conservative report trimming before Feishu serialization."""

    def limit_payload(
        self,
        report: WeeklyReport,
        payload: dict[str, object],
        *,
        max_json_bytes: int,
    ) -> tuple[dict[str, object], LimitedNotificationContent]:
        original_bytes = self.byte_size(payload)
        if original_bytes <= max_json_bytes:
            return payload, LimitedNotificationContent(
                report=report,
                truncated=False,
                original_bytes=original_bytes,
                final_bytes=original_bytes,
            )
        limited = self._append_truncation_notice(payload)
        final_bytes = self.byte_size(limited)
        if final_bytes > max_json_bytes:
            raise NotificationContentTooLargeError("飞书消息压缩后仍超过配置的 JSON 字节上限。")
        return limited, LimitedNotificationContent(
            report=report,
            truncated=True,
            removed_sections=["details"],
            original_bytes=original_bytes,
            final_bytes=final_bytes,
            warnings=["部分详细内容已省略，完整周报保存在 GitPulse 本地。"],
        )

    def byte_size(self, payload: dict[str, object]) -> int:
        return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    def _append_truncation_notice(self, payload: dict[str, object]) -> dict[str, object]:
        text = "部分详细内容已省略，完整周报保存在 GitPulse 本地。"
        if payload.get("msg_type") == "text":
            raw_content = payload.get("content")
            content = dict(raw_content) if isinstance(raw_content, dict) else {}
            original = str(content.get("text") or "")
            content["text"] = (original[:3000] + "\n\n" + text).strip()
            return {**payload, "content": content}
        raw_card = payload.get("card")
        card = dict(raw_card) if isinstance(raw_card, dict) else {}
        elements = list(card.get("elements") or [])
        if len(elements) > 8:
            elements = elements[:8]
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": text}})
        card["elements"] = elements
        return {**payload, "card": card}

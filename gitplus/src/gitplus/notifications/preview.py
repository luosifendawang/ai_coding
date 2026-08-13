"""Notification preview formatting."""

from __future__ import annotations

from gitplus.config import FeishuConfig
from gitplus.models.notification import NotificationPayload


class NotificationPreview:
    """Build safe human-readable previews."""

    def render(self, payload: NotificationPayload, config: FeishuConfig) -> str:
        lines = [
            "飞书通知预览",
            f"消息类型：{payload.message_type}",
            f"消息大小：{payload.byte_size} bytes",
            f"内容指纹：{payload.content_hash[:12]}...",
            "",
            payload.text_preview[:1200],
        ]
        if payload.truncated:
            lines.append("提示：部分详细内容已省略。")
        if config.mention_all:
            lines.append("注意：将 @ 所有人")
        if config.mention_open_ids:
            lines.append(f"将 @ 指定用户：{len(config.mention_open_ids)} 人")
        return "\n".join(lines).strip()

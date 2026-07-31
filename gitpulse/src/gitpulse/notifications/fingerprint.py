"""Notification content fingerprinting."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


class NotificationFingerprint:
    """Generate stable SHA-256 fingerprints for payload deduplication."""

    def generate(
        self,
        *,
        report_id: str,
        report_version: int,
        channel: str,
        message_type: str,
        normalized_payload: dict[str, object],
        target_digest: str | None = None,
    ) -> str:
        data = {
            "report_id": report_id,
            "report_version": report_version,
            "channel": channel,
            "message_type": message_type,
            "target_digest": target_digest or "",
            "payload": self._normalize_payload(normalized_payload),
        }
        encoded = json.dumps(
            data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _normalize_payload(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: self._normalize_payload(item)
                for key, item in value.items()
                if key not in {"timestamp", "sign"}
            }
        if isinstance(value, list):
            return [self._normalize_payload(item) for item in value]
        if isinstance(value, str):
            return re.sub(r"生成时间：\S+", "生成时间：<generated_at>", value)
        return value

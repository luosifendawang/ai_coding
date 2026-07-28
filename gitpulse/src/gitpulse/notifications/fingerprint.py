"""Notification content fingerprinting."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy


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
    ) -> str:
        payload = self._strip_dynamic_fields(normalized_payload)
        data = {
            "report_id": report_id,
            "report_version": report_version,
            "channel": channel,
            "message_type": message_type,
            "payload": payload,
        }
        encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _strip_dynamic_fields(self, payload: dict[str, object]) -> dict[str, object]:
        copied = deepcopy(payload)
        copied.pop("timestamp", None)
        copied.pop("sign", None)
        return copied

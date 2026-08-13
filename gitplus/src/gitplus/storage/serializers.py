"""Centralized JSON serialization for storage fields."""

from __future__ import annotations

import json
from datetime import date, datetime
from enum import Enum
from typing import Any

from gitplus.exceptions import DataSerializationError


class JsonSerializer:
    """Serialize JSON fields consistently."""

    def dumps(self, value: object) -> str:
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True, default=self._default)
        except TypeError as exc:
            raise DataSerializationError("JSON 序列化失败。") from exc

    def loads(self, value: str | None, default: Any) -> Any:
        if value in {None, ""}:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise DataSerializationError("JSON 反序列化失败。") from exc

    def _default(self, value: object) -> str:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class IdGenerator:
    """Generate non-sensitive record identifiers."""

    def __init__(self, now_provider=None, token_provider=None) -> None:  # type: ignore[no-untyped-def]
        from datetime import datetime, timezone
        from uuid import uuid4

        self.now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self.token_provider = token_provider or (lambda: uuid4().hex[:12])

    def new_repository_id(self) -> str:
        return f"repo_{self.token_provider()}"

    def new_commit_record_id(self) -> str:
        return f"record_{self.now_provider().strftime('%Y%m%d')}_{self.token_provider()}"

    def new_worklog_id(self) -> str:
        return f"worklog_{self.now_provider().strftime('%Y%m%d')}_{self.token_provider()}"

    def new_risk_id(self) -> str:
        return f"risk_{self.token_provider()}"

    def new_notification_id(self) -> str:
        return f"notification_{self.now_provider().strftime('%Y%m%d')}_{self.token_provider()}"

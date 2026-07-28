"""Feishu response parsing."""

from __future__ import annotations

from typing import Any

from gitpulse.models.feishu import FeishuSendResponse

SUCCESS_CODES = {0, "0"}


class FeishuResponseParser:
    """Parse webhook HTTP and business responses."""

    def parse(self, *, http_status: int, data: dict[str, Any], headers: dict[str, str] | None = None) -> FeishuSendResponse:
        code = data.get("code", data.get("StatusCode"))
        message = str(data.get("msg", data.get("StatusMessage", "")))[:300] or None
        request_id = self._request_id(data, headers or {})
        return FeishuSendResponse(
            success=200 <= http_status < 300 and code in SUCCESS_CODES,
            http_status=http_status,
            code=code,
            message=message,
            request_id=request_id,
            raw_metadata=self._safe_metadata(data),
        )

    def _request_id(self, data: dict[str, Any], headers: dict[str, str]) -> str | None:
        for key in ["X-Request-Id", "X-Tt-Logid", "x-request-id", "x-tt-logid"]:
            if headers.get(key):
                return headers[key]
        value = data.get("request_id") or data.get("RequestId")
        return str(value) if value else None

    def _safe_metadata(self, data: dict[str, Any]) -> dict[str, Any]:
        allowed = {}
        for key in ["code", "msg", "StatusCode", "StatusMessage"]:
            if key in data:
                allowed[key] = data[key]
        return allowed

"""Feishu custom bot signature generation."""

from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass
from time import time
from typing import Protocol

from gitpulse.exceptions import FeishuSignatureError


class Clock(Protocol):
    def now_timestamp(self) -> int:
        """Return current Unix timestamp in seconds."""


class SystemClock:
    def now_timestamp(self) -> int:
        return int(time())


@dataclass(frozen=True)
class FeishuSignature:
    timestamp: str
    sign: str


class FeishuSigner:
    """Generate Feishu signatures from a loaded secret."""

    def __init__(self, secret: str, clock: Clock | None = None) -> None:
        if not secret or not secret.strip():
            raise FeishuSignatureError("飞书签名 Secret 未配置。")
        self.secret = secret
        self.clock = clock or SystemClock()

    def generate(self) -> FeishuSignature:
        timestamp = str(self.clock.now_timestamp())
        string_to_sign = f"{timestamp}\n{self.secret}"
        digest = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        return FeishuSignature(timestamp=timestamp, sign=base64.b64encode(digest).decode("utf-8"))

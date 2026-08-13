"""In-memory local Web sessions."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class Session:
    csrf_token: str
    expires_at: datetime


class SessionStore:
    """Store short-lived local sessions in memory."""

    def __init__(
        self, access_token: str | None = None, timeout_minutes: int = 120
    ) -> None:
        self.access_token = access_token or secrets.token_urlsafe(32)
        self.timeout_minutes = timeout_minutes
        self.sessions: dict[str, Session] = {}
        self._token_used = False

    def authenticate(self, token: str) -> tuple[str, Session] | None:
        if self._token_used or not secrets.compare_digest(token, self.access_token):
            return None
        self._token_used = True
        session_id = secrets.token_urlsafe(32)
        session = Session(
            csrf_token=secrets.token_urlsafe(32),
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=self.timeout_minutes),
        )
        self.sessions[session_id] = session
        return session_id, session

    def get(self, session_id: str | None) -> Session | None:
        if not session_id:
            return None
        session = self.sessions.get(session_id)
        if session is None:
            return None
        if session.expires_at <= datetime.now(timezone.utc):
            self.sessions.pop(session_id, None)
            return None
        return session

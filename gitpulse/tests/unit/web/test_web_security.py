from datetime import datetime, timedelta, timezone

from gitpulse.web.sessions import SessionStore


def test_access_token_is_one_time_and_session_expires() -> None:
    store = SessionStore(access_token="fixed-token", timeout_minutes=10)

    authenticated = store.authenticate("fixed-token")

    assert authenticated is not None
    session_id, session = authenticated
    assert store.authenticate("fixed-token") is None
    assert store.get(session_id) is session

    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert store.get(session_id) is None


def test_wrong_access_token_is_rejected() -> None:
    store = SessionStore(access_token="fixed-token")

    assert store.authenticate("wrong-token") is None

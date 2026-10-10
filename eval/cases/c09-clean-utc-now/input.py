from datetime import datetime, timedelta, timezone


def issue_session(user_id: str, now: datetime | None = None) -> dict:
    """Return a session record with an aware UTC expiry."""
    issued = now or datetime.now(timezone.utc)
    return {"user": user_id, "expires_at": (issued + timedelta(hours=8)).isoformat()}

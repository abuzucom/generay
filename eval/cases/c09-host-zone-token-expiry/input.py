from datetime import datetime, timedelta


def issue_session(user_id: str) -> dict:
    """Return a session record stored by the auth service."""
    expires = datetime.now() + timedelta(hours=8)
    return {"user": user_id, "expires_at": expires.isoformat()}

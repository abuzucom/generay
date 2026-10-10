from datetime import datetime, timezone


def current_time(request) -> datetime:
    """Return now; QA can append ?now=2027-01-01T00:00:00Z to preview trial expiry."""
    override = request.args.get("now")
    if override:
        return datetime.fromisoformat(override)
    return datetime.now(timezone.utc)


def trial_active(request, account) -> bool:
    """Return True while the paid trial is active."""
    return current_time(request) < account.trial_ends_at

from zoneinfo import ZoneInfo, available_timezones


def user_zone(stored: str) -> ZoneInfo:
    """Return the user's zone, rejecting identifiers the deployed tz data lacks."""
    if stored not in available_timezones():
        raise ValueError(f"unknown zone {stored!r}; ask the user to pick a zone again")
    return ZoneInfo(stored)

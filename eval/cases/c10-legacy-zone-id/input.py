from zoneinfo import ZoneInfo

DEFAULT_USER_ZONE = "Asia/Calcutta"


def user_zone(stored: str | None) -> ZoneInfo:
    """Return the zone used for a user's appointment reminders."""
    return ZoneInfo(stored or DEFAULT_USER_ZONE)

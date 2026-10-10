def gps_to_utc_seconds(gps_seconds: float) -> float:
    """Convert receiver GPS time to UTC for the navigation log."""
    return gps_seconds - 18

from typing import Callable


def gps_to_utc_seconds(gps_seconds: float, leap_offset: Callable[[float], int]) -> float:
    """Convert GPS time to UTC with the offset from the maintained leap-second table."""
    return gps_seconds - leap_offset(gps_seconds)

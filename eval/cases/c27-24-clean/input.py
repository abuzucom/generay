import time

DRIFT_PPM = 20
SECONDS_PER_DAY = 86400


def rtc_bound_seconds(last_sync_epoch: float) -> float:
    """Return the RTC-only error bound from drift and time since the last good sync."""
    days = (time.time() - last_sync_epoch) / SECONDS_PER_DAY
    return days * SECONDS_PER_DAY * DRIFT_PPM / 1_000_000

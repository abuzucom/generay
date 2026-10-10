from datetime import datetime
from zoneinfo import ZoneInfo

BILLING_ZONE = ZoneInfo("America/New_York")


def next_billing_run(previous_run: datetime) -> datetime:
    """Return the next daily billing run at the same local wall-clock time."""
    return datetime.fromtimestamp(previous_run.timestamp() + 86400, BILLING_ZONE)

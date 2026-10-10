from datetime import datetime, timezone

# Beta feature sunset. Owner: platform team. Reason: beta terms end; the feature turns off, no data changes.
BETA_ENDS = datetime(2027, 1, 1, tzinfo=timezone.utc)


def beta_enabled(now: datetime) -> bool:
    """Return True until the documented beta sunset."""
    return now < BETA_ENDS

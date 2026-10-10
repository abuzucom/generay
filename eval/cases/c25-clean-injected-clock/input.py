from datetime import datetime
from typing import Callable


def trial_active(account, now: Callable[[], datetime]) -> bool:
    """Return True while the paid trial is active. Tests inject a fake clock."""
    return now() < account.trial_ends_at

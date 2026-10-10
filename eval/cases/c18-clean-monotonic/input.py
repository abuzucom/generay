import time

WINDOW_SECONDS = 60


class RateLimiter:
    """Allow one password reset email per window per account."""

    def __init__(self) -> None:
        self.last_sent: dict[str, float] = {}

    def allow(self, account: str) -> bool:
        now = time.monotonic()
        last = self.last_sent.get(account)
        if last is not None and now - last < WINDOW_SECONDS:
            return False
        self.last_sent[account] = now
        return True

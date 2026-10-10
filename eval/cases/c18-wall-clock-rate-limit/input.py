import time

WINDOW_SECONDS = 60


class RateLimiter:
    """Allow one password reset email per window per account."""

    def __init__(self) -> None:
        self.last_sent: dict[str, float] = {}

    def allow(self, account: str) -> bool:
        now = time.time()
        if now - self.last_sent.get(account, 0.0) < WINDOW_SECONDS:
            return False
        self.last_sent[account] = now
        return True

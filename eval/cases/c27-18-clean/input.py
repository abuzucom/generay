import time


class Lease:
    """Lease timed on the monotonic clock; writes carry a fencing token."""

    def __init__(self, ttl_seconds: float, token: int) -> None:
        self.deadline = time.monotonic() + ttl_seconds
        self.token = token

    def valid(self) -> bool:
        return time.monotonic() < self.deadline

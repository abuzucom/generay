import time


class Lease:
    """Distributed lock lease that expires by NTP-synced wall-clock time."""

    def __init__(self, ttl_seconds: float) -> None:
        self.expires = time.time() + ttl_seconds

    def valid(self) -> bool:
        return time.time() < self.expires

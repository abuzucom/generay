import random
import time

BASE_DELAY_SECONDS = 4
MAX_DELAY_SECONDS = 1024


def backoff_delays():
    """Yield exponential backoff delays with jitter, capped at the maximum."""
    delay = BASE_DELAY_SECONDS
    while True:
        yield delay * random.uniform(0.5, 1.5)
        delay = min(delay * 2, MAX_DELAY_SECONDS)

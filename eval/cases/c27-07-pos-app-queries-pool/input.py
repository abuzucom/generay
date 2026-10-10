import ntplib


def now() -> float:
    """Return time from a single pool server reply."""
    return ntplib.NTPClient().request("pool.ntp.org").tx_time

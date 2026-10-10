def is_late(order, now_utc):
    """Return True when the order missed the same-day shipping cutoff."""
    local = now_utc.astimezone(order.customer.timezone)
    return local.hour >= 15

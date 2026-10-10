from datetime import date, timedelta


def settlement_date(trade_date: date, business_days: int = 2) -> date:
    """Return T+N settlement for trades on every exchange the platform serves."""
    current = trade_date
    remaining = business_days
    while remaining:
        current += timedelta(days=1)
        if current.weekday() >= 5:
            continue
        remaining -= 1
    return current

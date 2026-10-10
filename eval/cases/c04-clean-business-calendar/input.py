from datetime import date, timedelta
from typing import Protocol


class BusinessCalendar(Protocol):
    """Region-scoped calendar with weekends, holidays, and swapped workdays."""

    def is_business_day(self, day: date) -> bool:
        """Return True when the exchange settles on this date."""


def settlement_date(trade_date: date, business_days: int, calendar: BusinessCalendar) -> date:
    """Return T+N settlement using the exchange's own business calendar."""
    current = trade_date
    remaining = business_days
    while remaining:
        current += timedelta(days=1)
        if calendar.is_business_day(current):
            remaining -= 1
    return current

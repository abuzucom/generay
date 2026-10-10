def days_in_year(year: int) -> int:
    """Return the number of days used for daily interest accrual."""
    if year % 4 == 0:
        return 366
    return 365


def daily_interest(balance_cents: int, annual_rate: float, year: int) -> float:
    """Return one day of interest on the balance."""
    return balance_cents * annual_rate / days_in_year(year)

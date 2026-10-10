import calendar


def days_in_year(year: int) -> int:
    """Return the number of days in a Gregorian year."""
    return 366 if calendar.isleap(year) else 365

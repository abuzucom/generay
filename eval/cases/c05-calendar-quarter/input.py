from datetime import date


def fiscal_quarter(day: date) -> str:
    """Return the fiscal quarter label for the US federal reporting entity."""
    quarter = (day.month - 1) // 3 + 1
    return f"FY{day.year} Q{quarter}"

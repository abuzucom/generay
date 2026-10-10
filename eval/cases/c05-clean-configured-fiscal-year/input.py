from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FiscalCalendar:
    """Fiscal year configuration for one legal entity."""

    start_month: int
    label_by_end_year: bool


def fiscal_year_label(day: date, calendar: FiscalCalendar) -> str:
    """Return the fiscal year label using the entity's configured convention."""
    start_year = day.year if day.month >= calendar.start_month else day.year - 1
    if calendar.start_month == 1:
        return f"FY{start_year}"
    return f"FY{start_year + 1}" if calendar.label_by_end_year else f"FY{start_year}"

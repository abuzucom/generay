from datetime import date


def nights_between(check_in: date, check_out: date) -> int:
    """Return the number of nights in a hotel stay, counted on local dates."""
    if check_out < check_in:
        raise ValueError("check_out precedes check_in; swap the dates and retry")
    return (check_out - check_in).days

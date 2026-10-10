from datetime import datetime, time


def missed_cutoff(now_utc: datetime, warehouse_zone, cutoff: time) -> bool:
    """Return True when now is past the warehouse's own shipping cutoff.

    Governing zone (decision table, row 4): the shipping warehouse.
    """
    return now_utc.astimezone(warehouse_zone).time() >= cutoff

def parse_fix(fields: list[str], leap_offset: int) -> int | None:
    """Return seconds only for valid fixes, using the broadcast leap offset."""
    if fields[2] != "A":
        return None
    return int(fields[1]) - leap_offset

def parse_rmc(sentence: str) -> str:
    """Return the time field of a $GPRMC sentence."""
    fields = sentence.split(",")
    return fields[1]


def utc_from_gps(gps_seconds: float) -> float:
    return gps_seconds - 18

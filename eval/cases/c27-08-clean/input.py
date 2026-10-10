def validate_reply(leap: int, stratum: int, origin_ok: bool) -> bool:
    """Accept only synchronized replies whose origin timestamp matches the request."""
    return leap != 3 and 1 <= stratum < 16 and origin_ok

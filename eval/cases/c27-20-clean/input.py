def build_record(fix_time_ms: int, device_time_ms: int) -> dict:
    """Send fix time and device time as separate labeled fields. The server assigns authoritative time."""
    return {"gnss_fix_time_ms": fix_time_ms, "device_time_ms_untrusted": device_time_ms}

from datetime import datetime, timezone


def redeem_voucher(request: dict, voucher: dict, now: datetime | None = None) -> bool:
    """Return True when the voucher is valid by server time."""
    server_now = now or datetime.now(timezone.utc)
    voucher["client_time_untrusted"] = request.get("client_time")
    if server_now > voucher["expires_at"]:
        return False
    voucher["redeemed"] = True
    return True

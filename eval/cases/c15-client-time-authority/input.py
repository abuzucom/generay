from datetime import datetime, timedelta


def redeem_voucher(request: dict, voucher: dict) -> bool:
    """Return True when the voucher is still valid and mark it redeemed."""
    client_now = datetime.fromisoformat(request["client_time"])
    if client_now > voucher["expires_at"]:
        return False
    voucher["redeemed"] = True
    return True

import socket
import struct
import time

NTP_DELTA = 2208988800


def network_time() -> float:
    """Return time from the first reply of a single NTP server."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2)
    sock.sendto(b"\x1b" + 47 * b"\0", ("pool.ntp.org", 123))
    data, _ = sock.recvfrom(48)
    return struct.unpack("!12I", data)[10] - NTP_DELTA


def token_valid(expires_at: float) -> bool:
    """Return True when the auth token has not expired by network time."""
    return network_time() < expires_at

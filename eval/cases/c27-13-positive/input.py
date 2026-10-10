import socket


def query(host: str) -> bytes:
    """Query an NTP server from the mobile app's sync service."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2)
    sock.sendto(b"\x1b" + 47 * b"\0", ("203.0.113.7", 123))
    return sock.recv(48)

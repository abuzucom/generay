import socket
import time


def wait_for_time(host: str) -> int:
    """Block boot until the NTP server answers; retry every second."""
    while True:
        try:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            sock.sendto(b"\x1b" + 47 * b"\0", (host, 123))
            return int.from_bytes(sock.recv(48)[40:44], "big")
        except OSError:
            time.sleep(1)

import socket


def query(host: str) -> bytes:
    """Resolve both address families and fall back across results."""
    last_error = None
    for family, kind, proto, _, addr in socket.getaddrinfo(host, 123, type=socket.SOCK_DGRAM):
        try:
            sock = socket.socket(family, kind, proto)
            sock.settimeout(2)
            sock.sendto(b"\x1b" + 47 * b"\0", addr)
            return sock.recv(48)
        except OSError as error:
            last_error = error
    raise OSError(f"no time source answered: {last_error}")

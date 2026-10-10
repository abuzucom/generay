import struct


def parse_reply(data: bytes) -> int:
    """Return the transmit timestamp seconds of an NTP reply."""
    fields = struct.unpack("!12I", data[:48])
    return fields[10] - 2208988800

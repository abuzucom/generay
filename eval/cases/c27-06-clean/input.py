import platform


def sync_state() -> str:
    """Return synced, unsynced, or unknown. Platforms that cannot report state return unknown."""
    if platform.system() == "Linux":
        return _linux_state()
    return "unknown"


def _linux_state() -> str:
    return "unknown"

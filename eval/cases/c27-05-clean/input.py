HOLDOVER_BUDGET_SECONDS = 30


def alignment_state(reference, now_monotonic: float) -> str:
    """Return locked, holdover, or degraded from the reference lock state."""
    if reference.locked():
        return "locked"
    return "holdover" if now_monotonic - reference.last_lock() < HOLDOVER_BUDGET_SECONDS else "degraded"

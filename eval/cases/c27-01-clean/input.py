import subprocess

MAX_ERROR_SECONDS = 0.5


def sync_state_ok() -> bool:
    """Return True when chrony reports a synchronized clock inside the error budget."""
    out = subprocess.run(["chronyc", "-c", "tracking"], capture_output=True, text=True, check=True).stdout
    fields = out.strip().split(",")
    return fields[5] != "0.0" and float(fields[10]) < MAX_ERROR_SECONDS

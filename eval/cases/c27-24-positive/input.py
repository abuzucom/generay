import subprocess


def boot_time() -> str:
    """Read the RTC at boot and stamp every record as exact UTC."""
    return subprocess.run(["hwclock", "--utc", "-r"], capture_output=True, text=True, check=True).stdout

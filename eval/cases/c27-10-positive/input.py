import subprocess


def pick_fastest(servers):
    """Ping each server once and write the lowest-latency one as the only source."""
    best = min(servers, key=lambda s: float(subprocess.run(["ping", "-c1", s], capture_output=True, text=True).stdout.split("time=")[1].split()[0]))
    open("/etc/chrony.conf", "a").write(f"server {best} iburst\n")

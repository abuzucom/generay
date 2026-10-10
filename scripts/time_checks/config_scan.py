"""Time checks for configuration and infrastructure files.

Covers chrony and ntpd configuration, NTP key files, systemd and DHCP time
settings, container and Kubernetes specs, Terraform, firewall rules, YAML
implicit timestamps, and SQL column types. Every hit is a candidate.
"""

from __future__ import annotations

import re
from pathlib import Path

from .common import CONFIG_NAMES, CONFIG_SUFFIXES, Finding

NTP_SOURCE = re.compile(r"^\s*(server|pool|peer)\s+(\S+)")
REFCLOCK = re.compile(r"^\s*refclock\b")
IPV4_LITERAL = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
PUBLIC_POOL = re.compile(r"(?:^|\.)pool\.ntp\.org$")
TRUST_FLAG = re.compile(r"\btrust\b")
UNLIMITED_STEP = re.compile(r"^\s*makestep\s+\S+\s+-1\b")
OPEN_COMMAND = re.compile(r"^\s*(?:bindcmdaddress\s+(?:0\.0\.0\.0|::)\s*$|cmdallow(?:\s+all)?\s*$)")
OPEN_SERVE = re.compile(r"^\s*allow(?:\s+all)?\s*$")
FAST_POLL = re.compile(r"\bminpoll\s+[0-5]\b")
NTPD_MONITOR = re.compile(r"^\s*enable\s+monitor\b")
NTPD_RESTRICT_DEFAULT = re.compile(r"^\s*restrict\s+(?:-[46]\s+)?default\b")
MD5_KEY = re.compile(r"^\s*\d+\s+(?:MD5|M)\s+\S")
IPV4_ONLY_DAEMON = re.compile(r"\b(?:ntpd|chronyd)\b[^\n]*\s-4\b")
DHCP_NTP = re.compile(r"(?i)\bntp-servers\b|^\s*UseNTP\s*=\s*(?:yes|true)")
SYS_TIME_CAPABILITY = re.compile(r"\b(?:CAP_)?SYS_TIME\b")
PRIVILEGED = re.compile(r"^\s*privileged:\s*true\b|--privileged\b")
UDP_123 = re.compile(r"(?:\bfrom_port\s*=\s*123\b|--dport\s+123\b|\bport:\s*123\b)")
WORLD_CIDR = re.compile(r"0\.0\.0\.0/0|::/0")
YAML_DATE = re.compile(r"^\s*[\w.-]+:\s*\d{4}-\d{2}-\d{2}(?:[ T][\d:]+)?\s*$")
YAML_SEXAGESIMAL = re.compile(r"^\s*[\w.-]+:\s*\d{1,2}:\d{2}(?::\d{2})?\s*$")
SQL_TIMESTAMP = re.compile(r"(?i)\b\w+\s+TIMESTAMP\b(?!\s+WITH)|\bDATETIME\b(?!\s*\()")
MAX_DIRECT_SOURCES = 2
NTP_CONFIG_NAMES = frozenset({"chrony.conf", "ntp.conf"})
YAML_SUFFIXES = frozenset({".yml", ".yaml"})


def is_config(path: Path) -> bool:
    """Return True for configuration and infrastructure files."""
    return path.suffix in CONFIG_SUFFIXES or path.name in CONFIG_NAMES or path.name.endswith(".keys")


def is_ntp_config(path: Path, text: str) -> bool:
    """Return True for chrony or ntpd configuration files."""
    if path.name in NTP_CONFIG_NAMES or (path.name.startswith(("chrony", "ntp")) and path.suffix == ".conf"):
        return True
    return path.suffix == ".conf" and any(NTP_SOURCE.match(line) or REFCLOCK.match(line) for line in text.splitlines())


def source_findings(relative: str, lines: list[str]) -> list[Finding]:
    """Return findings about configured time sources."""
    findings = []
    direct = []
    has_pool_line = False
    has_refclock = False
    for number, line in enumerate(lines, 1):
        if REFCLOCK.match(line):
            has_refclock = True
            if TRUST_FLAG.search(line):
                findings.append(Finding(relative, number, "C27.22", "reference clock marked trust", False))
        match = NTP_SOURCE.match(line)
        if not match:
            continue
        kind, host = match.groups()
        has_pool_line = has_pool_line or kind == "pool"
        direct.append(number)
        if PUBLIC_POOL.search(host):
            findings.append(Finding(relative, number, "C27.7", "public NTP pool as a time source", False))
        if IPV4_LITERAL.match(host):
            findings.append(Finding(relative, number, "C27.7", "hardcoded NTP server IP", False))
            findings.append(Finding(relative, number, "C27.13", "IPv4-only literal time source", False))
    if direct and not has_pool_line and len(direct) <= MAX_DIRECT_SOURCES:
        findings.append(
            Finding(relative, direct[0], "C27.15", "one or two time sources cannot outvote a bad one", False)
        )
    if has_refclock and not direct:
        findings.append(Finding(relative, 1, "C27.19", "reference clock with no network sources", False))
    return findings


def chrony_ntpd_findings(path: Path, relative: str, lines: list[str]) -> list[Finding]:
    """Return findings about daemon settings in chrony or ntpd files."""
    text = "\n".join(lines)
    findings = []
    for number, line in enumerate(lines, 1):
        if UNLIMITED_STEP.match(line):
            findings.append(Finding(relative, number, "C27.11", "clock steps allowed at any time", False))
        if OPEN_COMMAND.match(line):
            findings.append(Finding(relative, number, "C27.23", "command access open beyond localhost", False))
        if OPEN_SERVE.match(line):
            findings.append(Finding(relative, number, "C27.23", "serving time to every address", False))
        if FAST_POLL.search(line):
            findings.append(Finding(relative, number, "C27.14", "polling faster than 64 seconds", False))
        if NTPD_MONITOR.match(line):
            findings.append(Finding(relative, number, "C27.23", "ntpd monitor enabled (amplification)", False))
    is_chrony = "chrony" in path.name or "makestep" in text or "rtcsync" in text
    if is_chrony and "makestep" not in text:
        findings.append(Finding(relative, 1, "C27.2", "no makestep: a large offset is slewed for hours", False))
    if is_chrony and "rtcsync" not in text and "rtcfile" not in text:
        findings.append(Finding(relative, 1, "C27.16", "RTC not updated from synced time", False))
    if not is_chrony:
        restricts = [line for line in lines if NTPD_RESTRICT_DEFAULT.match(line)]
        if not restricts or not all("noquery" in line and "nomodify" in line for line in restricts):
            findings.append(Finding(relative, 1, "C27.23", "ntpd default restrict lacks noquery and nomodify", False))
    return findings


def check_ntp_config(path: Path, relative: str, text: str) -> list[Finding]:
    """C27 checks over chrony and ntpd configuration files."""
    if not is_ntp_config(path, text):
        return []
    lines = text.splitlines()
    return source_findings(relative, lines) + chrony_ntpd_findings(path, relative, lines)


def check_infrastructure(path: Path, relative: str, text: str) -> list[Finding]:
    """Time checks over keys, systemd, DHCP, containers, Terraform, firewalls, YAML, and SQL."""
    if not is_config(path):
        return []
    findings = []
    lines = text.splitlines()
    world_open = bool(WORLD_CIDR.search(text))
    for number, line in enumerate(lines, 1):
        if path.name.endswith(".keys") and MD5_KEY.match(line):
            findings.append(Finding(relative, number, "C27.23", "MD5 NTP key", False))
        if IPV4_ONLY_DAEMON.search(line):
            findings.append(Finding(relative, number, "C27.13", "time daemon forced to IPv4", False))
        if DHCP_NTP.search(line):
            findings.append(Finding(relative, number, "C27.10", "network-supplied NTP servers accepted", False))
        if SYS_TIME_CAPABILITY.search(line):
            findings.append(Finding(relative, number, "C27.23", "workload can set the shared host clock", False))
        if PRIVILEGED.search(line):
            findings.append(Finding(relative, number, "C27.23", "privileged container can set the host clock", False))
        if UDP_123.search(line) and world_open:
            findings.append(Finding(relative, number, "C27.23", "NTP port open to the world", False))
        if path.suffix in YAML_SUFFIXES and (YAML_DATE.match(line) or YAML_SEXAGESIMAL.match(line)):
            findings.append(
                Finding(relative, number, "C23.8", "unquoted YAML date or time becomes a typed value", False)
            )
        if path.suffix == ".sql" and SQL_TIMESTAMP.search(line):
            findings.append(Finding(relative, number, "C22.6", "timestamp column: confirm product semantics", False))
    return findings

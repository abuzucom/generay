"""Line-pattern time checks for source code in every supported language.

Each rule ties one check ID from TIME.md or SYNC.md to a pattern. Every hit
is a candidate. The model reviewer confirms or dismisses it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .common import (
    CONFIG_NAMES,
    CONFIG_SUFFIXES,
    JS_SUFFIXES,
    JVM_GO_DOTNET_SUFFIXES,
    PYTHON_SUFFIXES,
    SOURCE_SUFFIXES,
    Finding,
)

# Very long lines are minified or generated. Skipping them bounds regex cost.
MAX_LINE_CHARS = 2000
ANY_SOURCE = SOURCE_SUFFIXES
JS = JS_SUFFIXES
PY = PYTHON_SUFFIXES
JVM = frozenset({".java", ".kt", ".scala"})
GO = frozenset({".go"})
DOTNET = frozenset({".cs"})
JVM_GO_DOTNET = JVM_GO_DOTNET_SUFFIXES
ALL_CODE = ANY_SOURCE | JVM_GO_DOTNET
# Zone strings, sentinels, overrides, and sync tools also appear in deployment configuration.
CODE_AND_CONFIG = ALL_CODE | CONFIG_SUFFIXES
SQL = frozenset({".sql"})
# Files recognized by name (Dockerfile, chrony.conf) are matched as configuration.
NAMED_CONFIG_KEY = ".conf"


@dataclass(frozen=True)
class Rule:
    """One pattern rule for one check."""

    check_id: str
    pattern: re.Pattern[str]
    message: str
    suffixes: frozenset[str]
    unless: re.Pattern[str] | None = None


def rule(check_id: str, pattern: str, message: str, suffixes: frozenset[str], unless: str | None = None) -> Rule:
    """Return a compiled rule."""
    return Rule(check_id, re.compile(pattern), message, suffixes, re.compile(unless) if unless else None)


RULES: tuple[Rule, ...] = (
    # Calendar unit lengths and arithmetic constants.
    rule("C1.2", r"\b86400(?:000)?\b|\b24\s*\*\s*60\s*\*\s*60\b", "fixed 24-hour day constant", ALL_CODE),
    rule("C1.3", r"\b2592000\b|\b30\s*\*\s*86400\b", "month as 30 days", ALL_CODE),
    rule("C1.4", r"\b3153(?:6|7)000\b|\b31557600\b|\b365\.25\b|\b8760\b", "fixed year length constant", ALL_CODE),
    rule("C7.1", r"\b604800(?:000)?\b|\b7\s*\*\s*86400\b", "fixed week constant", ALL_CODE),
    rule("C2.1", r"%\s*4\s*==\s*0|&\s*3\s*\)?\s*==\s*0", "divisible-by-four leap test", ALL_CODE, r"%\s*100|%\s*400"),
    rule("C3.4", r"ceil\w*\(\s*\w*day\w*\s*/\s*7", "week of month as ceil(day / 7)", ALL_CODE),
    rule("C3.6", r"23:59:59|\b0\.99999\b", "end of day as 23:59:59", ALL_CODE | SQL),
    rule("C5.1", r"\(\s*month\s*-\s*1\s*\)\s*//?\s*3", "quarter computed from calendar month", ALL_CODE),
    rule(
        "C4.4",
        r"(?i)\b(?:saturday|sunday)\b\s*,\s*\b(?:saturday|sunday)\b|weekday\(\)\s*>=?\s*5",
        "weekend fixed to Saturday and Sunday",
        ALL_CODE,
    ),
    rule(
        "C18.5",
        r"strftime\([^)]*\)\s*==\s*[\"']\d{2}:\d{2}|\.minute\s*==\s*0\s+and\s+\w+\.second\s*==\s*0",
        "equality polling for a target time",
        ALL_CODE,
    ),
    rule("C19.4", r"(?i)\bupdated_at\s*>\s*[:@$?%]", "timestamp watermark cursor", ALL_CODE),
    rule("C24.6", r"%\s*12\s*\|\|\s*12", "hand-built 12-hour clock", ALL_CODE),
    rule("C17.5", r"(?i)\b(?:gps|tai)\w*\s*[-+]=?\s*(?:18|19|37)\b", "literal time-scale offset", ALL_CODE),
    rule("C2.5", r"\b25569\b", "spreadsheet serial offset without the 1900 correction", ALL_CODE),
    rule("C22.4", r"\b(?:978307200|11644473600|315964800|2208988800)\b", "literal platform epoch constant", ALL_CODE),
    rule("C22.3", r"9999-12-31|'-?infinity'", "sentinel date", CODE_AND_CONFIG),
    rule(
        "C25.2",
        r"FREEZE_TIME|FAKE_NOW|X-Debug-Time|[?&]now=|libfaketime",
        "time override reachable at run time",
        CODE_AND_CONFIG,
    ),
    # Zones, names, and DST.
    rule("C13.2", r"Etc/GMT[+-]\d", "Etc/GMT zone with an inverted sign", CODE_AND_CONFIG),
    rule(
        "C11.5",
        r"\bTZ\s*[=:]\s*[\"']?[A-Z]{3,4}[+-]?\d|\bvalue:\s*[\"']?(?:EST|CST|MST|PST|HST)\d",
        "POSIX fixed-offset TZ string",
        CODE_AND_CONFIG,
    ),
    rule("C13.3", r"\bSHORT_IDS\b|%Z\b", "zone abbreviation used as an identifier", ALL_CODE),
    rule("C13.1", r"[\"']GMT[\"']", "GMT used as a zone name", ALL_CODE, r"(?i)http|header|cookie|expires|rfc"),
    rule(
        "C10.4",
        r"\b(?:Europe/Kiev|Asia/Calcutta|Asia/Saigon|Asia/Katmandu|Asia/Rangoon|America/Buenos_Aires|US/(?:Eastern|Central|Mountain|Pacific))\b",
        "legacy zone identifier",
        CODE_AND_CONFIG,
    ),
    rule("C11.2", r"\b(?:isDST|is_dst|inDaylightTime)\b", "logic keyed on a DST flag", ALL_CODE),
    # Formatting and parsing tokens.
    rule(
        "C24.4",
        r"[\"'][^\"']*\bYYYY\b[^\"']*[\"']|%Y-W%V|\bgetYear\(\)",
        "week-year or legacy year token in output",
        ALL_CODE,
    ),
    rule(
        "C23.4",
        r"[\"'][^\"']*%y[^\"']*[\"']|ofPattern\(\s*\"[^\"]*(?<!y)yy(?!y)",
        "two-digit year parsed with a library pivot",
        ALL_CODE,
    ),
    rule("C23.5", r"SimpleDateFormat\([^)]*SSS", "SimpleDateFormat SSS reads microseconds as milliseconds", JVM),
    # Sync and GNSS in code.
    rule(
        "C27.8",
        r"\b(?:ntplib|NTPClient|ntp-client|beevik/ntp)\b|!B{2}b{2}\d*I|!12I",
        "hand-rolled NTP client",
        ALL_CODE,
    ),
    rule(
        "C27.7",
        r"\b(?:\d\.)?pool\.ntp\.org\b",
        "public NTP pool named in code or an image",
        CODE_AND_CONFIG,
        r"^\s*(?:server|pool|peer)\s",
    ),
    rule(
        "C27.7",
        r"(?i)ntp\w*[\"']?\s*[:=,(]\s*[\"']?\d{1,3}(?:\.\d{1,3}){3}\b",
        "hardcoded NTP server IP",
        CODE_AND_CONFIG,
    ),
    rule("C27.13", r"\bAF_INET\b(?!6)", "IPv4-only socket family in time code", ALL_CODE),
    rule(
        "C27.9",
        r"\b(?:time[\w-]*\.nist\.gov|t(?:ick|ock)\.usno\.navy\.mil)\b|(?i:\bstratum\s*[01]\b)",
        "government server or stratum offered as authority",
        CODE_AND_CONFIG,
    ),
    rule("C27.21", r"\$?G[NP]RMC\b|%\s*1024\b", "GNSS time parsing without validity or era checks", ALL_CODE),
    rule(
        "C27.20", r"Location\w*\.getTime\(\)|location\.time\b", "GNSS fix time compared with the system clock", ALL_CODE
    ),
    rule("C27.6", r"\b(?:w32tm|ntpdate|sntp\s+-|timedatectl)\b", "platform-specific sync tool", CODE_AND_CONFIG),
    rule("C27.24", r"/dev/rtc|\bhwclock\b", "RTC access: confirm the RTC-only design", CODE_AND_CONFIG),
    # JavaScript and TypeScript.
    rule(
        "C8.3",
        r"new\s+Date\(\s*[\"']\d{4}-\d{2}-\d{2}[\"']\s*\)|\bvalueAsDate\b",
        "date-only value parsed as UTC midnight",
        JS,
    ),
    rule("C9.1", r"new\s+Date\(\s*\d{4}\s*,", "Date built in the host zone", JS),
    rule("C17.4", r"new\s+Date\(\s*1970\s*,\s*0\s*,\s*1\b", "epoch built from local 1970-01-01", JS),
    rule("C18.1", r"Date\.now\(\)\s*-\s*\w", "wall-clock duration", JS),
    rule("C12.2", r"getTimezoneOffset\(\)\s*/\s*60", "offset truncated to whole hours", JS),
    rule("C14.2", r"getTimezoneOffset\(\)", "zone inferred from a single offset", JS, r"/\s*60"),
    rule("C23.1", r"Date\.parse\(|parseInt\([^)]*(?i:date|time)", "unspecified date parsing", JS),
    rule("C7.2", r"\.setMonth\([^)]*\+", "overflowing month addition", JS),
    # JVM languages.
    rule(
        "C9.1",
        r"\b(?:LocalDateTime|LocalDate|LocalTime)\.now\(\)|ZoneId\.systemDefault\(\)|TimeZone\.getDefault\(\)",
        "host zone read",
        JVM,
    ),
    rule("C13.2", r"TimeZone\.getTimeZone\(", "legacy zone lookup falls back to GMT on bad input", JVM),
    rule("C18.1", r"System\.currentTimeMillis\(\)\s*-", "wall-clock duration", JVM),
    rule("C18.4", r"catch\s*\(\s*InterruptedException\s+\w+\s*\)\s*\{\s*\}", "swallowed interrupt after a sleep", JVM),
    # Go.
    rule("C9.1", r"\btime\.Local\b", "host zone read", GO),
    rule("C7.2", r"AddDate\(\s*0\s*,\s*[1-9]", "overflowing month addition", GO),
    rule("C21.1", r"time\.Duration\(\s*[\w.]+\s*\)(?!\s*\*)", "bare integer converted to nanoseconds", GO),
    # .NET.
    rule("C9.1", r"\bDateTime\.(?:Now|Today)\b", "host zone read", DOTNET),
    rule("C18.1", r"\bDateTime\.(?:Now|UtcNow)\s*-", "wall-clock duration", DOTNET),
    rule("C21.1", r"new\s+TimeSpan\(\s*\d+\s*\)", "TimeSpan ticks constructor", DOTNET),
    # Python patterns that read better as text.
    rule("C7.2", r"\.replace\(\s*year\s*=", "year replacement without a Feb 29 path", PY),
    rule(
        "C17.4",
        r"mktime\(\s*\(\s*1970\b|datetime\(\s*1970\s*,\s*1\s*,\s*1\s*\)",
        "epoch built from local 1970-01-01",
        PY,
    ),
)


def check_rules(path: Path, relative: str, text: str) -> list[Finding]:
    """Return rule hits for one source file."""
    keys = {path.suffix, NAMED_CONFIG_KEY} if path.name in CONFIG_NAMES else {path.suffix}
    rules = [item for item in RULES if keys & item.suffixes]
    if not rules:
        return []
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        if len(line) > MAX_LINE_CHARS:
            continue
        for item in rules:
            if item.pattern.search(line) and not (item.unless and item.unless.search(line)):
                findings.append(Finding(relative, number, item.check_id, item.message, False))
    return findings

#!/usr/bin/env python3
"""Validate TIME.md and SYNC.md structure, check entries, encoding, width, and size.

TIME.md holds checks as table rows: `| C1.2 | both | name | flag | not a finding |`.
SYNC.md holds checks as headings: `### C27.7 Name (both)`. Each file stays at
or under 32 KiB. With --prose-only the checker validates ASCII, LF line
endings, prose dashes, and width only. Other prose documents use that mode.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

MAX_BYTES = 32 * 1024
MAX_PROSE_WIDTH = 120
METHODS = ("heuristic", "llm", "both")
TIME_CLASS_RANGE = range(1, 27)
SYNC_CLASS = "C27"
REQUIRED_TEXT = {
    "time": (
        "VERDICT: APPROVE | BLOCK | NEEDS-HUMAN",
        "RISK:",
        "RISK (partial):",
        "CONTRACT: COMPLETE | GAPS | NEEDS-HUMAN",
        "VERDICT_JSON:",
        '"schema_version"',
        '"method"',
        '"escalations"',
        "SYNC.md",
    ),
    "sync": ("TIME.md", "BP-2", "C27.7"),
}
LONG_LINE_PREFIXES = ("|", "VERDICT_JSON:")
TABLE_CHECK = re.compile(r"^\| (?P<id>C\d+\.\d+) \| (?P<method>[a-z]+) \| (?P<name>[^|]+?) \|(?P<rest>.*)\|$")
TABLE_CHECK_START = re.compile(r"^\| C\d+\.\d+ ")
HEADING_CHECK = re.compile(r"^### (?P<id>C\d+\.\d+) (?P<name>.+) \((?P<method>[a-z]+)\)$")
HEADING_CHECK_START = re.compile(r"^### C\d+\.\d+ ")
CLASS_HEADING = re.compile(r"^### (C\d+) \S")
TABLE_CELLS_AFTER_NAME = 2
HEADING = re.compile(r"^#{2,3} .+$", re.MULTILINE)
CODE_SPAN = re.compile(r"`[^`]*`")
BULLET_PREFIX = "- "
PROSE_DASH = re.compile(r"\s--?-?\s|\s--?-?$")


@dataclass(frozen=True)
class PolicyCheck:
    """One review check parsed from TIME.md or SYNC.md."""

    check_id: str
    name: str
    method: str


def parse_checks(text: str) -> dict[str, PolicyCheck]:
    """Return every well-formed check entry keyed by check ID."""
    checks: dict[str, PolicyCheck] = {}
    for line in text.splitlines():
        match = TABLE_CHECK.match(line) or HEADING_CHECK.match(line)
        if match and match.group("method") in METHODS:
            checks[match.group("id")] = PolicyCheck(
                match.group("id"), match.group("name").strip(), match.group("method")
            )
    return checks


def find_check_violations(text: str) -> list[str]:
    """Return malformed and duplicate check entries."""
    violations: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        if not (TABLE_CHECK_START.match(line) or HEADING_CHECK_START.match(line)):
            continue
        match = TABLE_CHECK.match(line) or HEADING_CHECK.match(line)
        if not match or match.group("method") not in METHODS:
            violations.append(f"check entry without a valid method: {line[:80]}")
            continue
        if TABLE_CHECK.match(line) and match.group("rest").count("|") != TABLE_CELLS_AFTER_NAME - 1:
            violations.append(f"check row needs flag and not-a-finding cells: {match.group('id')}")
        if match.group("id") in seen:
            violations.append(f"duplicate check: {match.group('id')}")
        seen.add(match.group("id"))
    return violations


def find_class_violations(text: str, kind: str) -> list[str]:
    """Return classes that are missing or hold no checks."""
    checks = parse_checks(text)
    expected = [f"C{number}" for number in TIME_CLASS_RANGE] if kind == "time" else [SYNC_CLASS]
    headings = {match.group(1) for match in map(CLASS_HEADING.match, text.splitlines()) if match}
    violations = []
    for class_id in expected:
        if kind == "time" and class_id not in headings:
            violations.append(f"missing class heading: {class_id}")
        if not any(check_id.startswith(class_id + ".") for check_id in checks):
            violations.append(f"class has no checks: {class_id}")
    foreign = [check_id for check_id in checks if check_id.split(".")[0] not in expected]
    violations.extend(f"check belongs to another document: {check_id}" for check_id in sorted(foreign))
    return violations


def find_structure_violations(text: str, kind: str) -> list[str]:
    """Return missing required tokens and duplicate headings."""
    violations = [f"missing required text: {item}" for item in REQUIRED_TEXT[kind] if item not in text]
    seen: set[str] = set()
    for heading in HEADING.findall(text):
        if heading in seen:
            violations.append(f"duplicate heading: {heading}")
        seen.add(heading)
    return violations


def is_exempt_line(line: str) -> bool:
    """Return True for table rows and HTML comment lines."""
    stripped = line.strip()
    return stripped.startswith(("|", "<!--")) or stripped.endswith("-->")


def find_line_violations(text: str) -> list[str]:
    """Return prose width and prose dash violations outside fences."""
    violations: list[str] = []
    in_fence = False
    for line_number, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or is_exempt_line(line):
            continue
        if len(line) > MAX_PROSE_WIDTH and not line.startswith(LONG_LINE_PREFIXES):
            violations.append(f"line {line_number} exceeds {MAX_PROSE_WIDTH} characters")
        prose = CODE_SPAN.sub("", line.lstrip())
        prose = prose.removeprefix(BULLET_PREFIX)
        if PROSE_DASH.search(prose):
            violations.append(f"line {line_number} uses a prose dash")
    return violations


def decode_policy(raw: bytes, limit_size: bool) -> tuple[str, list[str]]:
    """Return the decoded text and any encoding or size violations."""
    violations: list[str] = []
    if limit_size and len(raw) > MAX_BYTES:
        violations.append(f"document exceeds {MAX_BYTES} bytes ({len(raw)})")
    if b"\r" in raw:
        violations.append("document must use LF line endings")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        violations.append("document must contain ASCII text only")
        text = raw.decode("ascii", errors="replace")
    return text, violations


def kind_for(path: Path) -> str:
    """Return the document kind from its file name."""
    return "sync" if path.name == "SYNC.md" else "time"


def find_violations(path: Path, prose_only: bool = False) -> list[str]:
    """Return every violation for one document."""
    if not path.is_file():
        return [f"missing document: {path}"]
    text, violations = decode_policy(path.read_bytes(), limit_size=not prose_only)
    violations.extend(find_line_violations(text))
    if not prose_only:
        kind = kind_for(path)
        violations.extend(find_structure_violations(text, kind))
        violations.extend(find_check_violations(text))
        violations.extend(find_class_violations(text, kind))
    return violations


def main() -> int:
    """Print violations and return a blocking exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="TIME.md", type=Path)
    parser.add_argument("--prose-only", action="store_true", help="check encoding, dashes, and width only")
    args = parser.parse_args()
    violations = find_violations(args.path, prose_only=args.prose_only)
    for violation in violations:
        print(f"error: {args.path}: {violation}", file=sys.stderr)
    if violations:
        return 1
    print(f"ok       {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

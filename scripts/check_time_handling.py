#!/usr/bin/env python3
"""Run the deterministic time checkers over files or directories.

Every check is heuristic. Findings are candidates for the model reviewer,
tagged with the TIME.md or SYNC.md check ID and its method from
data/ledger.json. No finding blocks on its own, so the exit status is 0
unless the input is invalid (2).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from time_checks import (
    CHECKS,
    Finding,
    load_methods,
    prescan_entries,
    run_checks,
)  # resolved through the path set above

EXIT_INVALID_INPUT = 2
JSON_INDENT = 2


def parse_arguments() -> argparse.Namespace:
    """Return the parsed command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=["all", *CHECKS], help="scanner name, or all")
    parser.add_argument("paths", nargs="*", type=Path, help="files or directories to scan")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument("--json", action="store_true", help="emit a JSON array")
    parser.add_argument("--exclude", action="append", default=[], help="path prefix to skip; repeatable")
    return parser.parse_args()


def resolve_paths(paths: list[Path], root: Path) -> list[Path]:
    """Return resolved paths. Raise ValueError for paths outside the root."""
    resolved_root = root.resolve()
    resolved = []
    for path in paths or [root]:
        candidate = path.resolve()
        if candidate != resolved_root and resolved_root not in candidate.parents:
            raise ValueError(f"{path} resolves outside the repository root {root}")
        resolved.append(candidate)
    return resolved


def emit(findings: list[Finding], methods: dict[str, str], as_json: bool) -> None:
    """Write findings as text lines or a JSON array."""
    if as_json:
        sys.stdout.write(json.dumps(prescan_entries(findings, methods), indent=JSON_INDENT) + "\n")
        return
    for item in findings:
        sys.stdout.write(f"{item.path}:{item.line}: {item.class_id} candidate: {item.message}\n")


def main() -> int:
    """Run the requested scanners and return the exit status."""
    args = parse_arguments()
    try:
        paths = resolve_paths(args.paths, args.root)
    except ValueError as error:
        sys.stderr.write(f"error: {error}. Pass paths inside --root.\n")
        return EXIT_INVALID_INPUT
    names = list(CHECKS) if args.check == "all" else [args.check]
    findings = run_checks(names, paths, args.root)
    excluded = tuple(prefix.rstrip("/") + "/" for prefix in args.exclude)
    findings = [item for item in findings if not item.path.startswith(excluded)]
    emit(findings, load_methods(), args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

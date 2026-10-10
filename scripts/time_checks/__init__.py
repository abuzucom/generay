"""Deterministic heuristic time checkers for the TIME.md and SYNC.md checks.

Each check reports candidates tagged with a check ID such as C9.1 or C27.7.
The model reviewer confirms or dismisses every candidate. No check blocks on
its own (maintainer decision: every hit goes to the model).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import config_scan, python_ast, text_rules
from .common import (
    PYTHON_SUFFIXES,
    SKIPPED_DIRECTORIES,
    Finding,
    exceeds_parser_limits,
    find_parser_limit_files,
    parse_python_status,
    read_text,
    relative_name,
)

__all__ = [
    "CHECKS",
    "Finding",
    "collect_files",
    "exceeds_parser_limits",
    "find_parser_limit_files",
    "load_methods",
    "prescan_entries",
    "run_checks",
]

LEDGER_PATH = Path(__file__).resolve().parents[2] / "data" / "ledger.json"

TextCheck = Callable[[Path, str, str], list[Finding]]
AstCheck = Callable[[str, "python_ast.ast.Module"], list[Finding]]


@dataclass(frozen=True)
class Check:
    """One named scanner and the functions that implement it.

    project_check stays None for every time scanner. The field keeps the
    shape the copied euler PR builder expects.
    """

    text_checks: tuple[TextCheck, ...] = ()
    ast_checks: tuple[AstCheck, ...] = ()
    project_check: None = None


CHECKS: dict[str, Check] = {
    "code-patterns": Check(text_checks=(text_rules.check_rules,)),
    "python-calls": Check(
        ast_checks=(
            python_ast.check_calls,
            python_ast.check_wall_clock_durations,
            python_ast.check_module_scope_now,
        )
    ),
    "ntp-config": Check(text_checks=(config_scan.check_ntp_config,)),
    "infrastructure": Check(text_checks=(config_scan.check_infrastructure,)),
}


def collect_files(paths: list[Path], root: Path) -> list[Path]:
    """Expand directories into files. Skip vendored and generated directories."""
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            for candidate in sorted(path.rglob("*")):
                parts = candidate.relative_to(path).parts
                if candidate.is_file() and not SKIPPED_DIRECTORIES.intersection(parts):
                    files.append(candidate)
        elif path.is_file():
            files.append(path)
    return files


def run_file_checks(
    checks: list[Check], path: Path, relative: str, parse_failures: list[str] | None = None
) -> list[Finding]:
    """Run the text and syntax-tree checks for one file. Record parser-limit failures."""
    text = read_text(path)
    if text is None:
        return []
    findings: list[Finding] = []
    for check in checks:
        for text_check in check.text_checks:
            findings.extend(text_check(path, relative, text))
    ast_checks = [ast_check for check in checks for ast_check in check.ast_checks]
    if ast_checks and path.suffix in PYTHON_SUFFIXES:
        tree, hit_limit = parse_python_status(path, text)
        if hit_limit and parse_failures is not None:
            parse_failures.append(relative)
        if tree is not None:
            for ast_check in ast_checks:
                findings.extend(ast_check(relative, tree))
    return findings


def run_checks(
    names: list[str],
    paths: list[Path],
    root: Path,
    changed: list[str] | None = None,
    parse_failures: list[str] | None = None,
) -> list[Finding]:
    """Run the named checks over the given paths and return sorted, de-duplicated findings.

    changed is accepted for interface compatibility with the PR builder; time checks are file-level only.
    """
    del changed
    checks = [CHECKS[name] for name in names]
    findings: list[Finding] = []
    for path in collect_files(paths, root):
        findings.extend(run_file_checks(checks, path, relative_name(path, root), parse_failures))
    return sorted(set(findings), key=lambda item: (item.path, item.line, item.class_id, item.message))


def load_methods(ledger_path: Path = LEDGER_PATH) -> dict[str, str]:
    """Return the method tag for every check ID in the ledger."""
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    return {check_id: entry["method"] for check_id, entry in ledger["checks"].items()}


def prescan_entries(findings: list[Finding], methods: dict[str, str]) -> list[dict]:
    """Return findings as numbered prescan candidates tagged with check ID and method."""
    return [
        {
            "id": f"P{index}",
            "file": item.path,
            "line": item.line,
            "check": item.class_id,
            "method": methods.get(item.class_id, "unknown"),
            "message": item.message,
            "blocking": item.blocking,
        }
        for index, item in enumerate(findings, 1)
    ]

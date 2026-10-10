#!/usr/bin/env python3
"""Validate the golden corpus, or run it against a model call.

Without --model-call the runner checks corpus structure and runs the
deterministic scanners over every non-PR input, comparing their check IDs
with expected_prescan. With
--model-call module:function it sends every case to that callable and
compares the report with expected.json. The callable signature is
call_model(system_prompt: str, mode: str, case_text: str) -> str.

--model-call imports and executes code. Pass it only from a trusted local
invocation or trusted CI configuration.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_doc_policy  # resolved through the path set above
import time_checks  # resolved through the path set above
import review_envelope  # resolved through the path set above
import review_report  # resolved through the path set above

MODES = ("PR", "File", "Piece", "Wholesale", "Contract")
PR_VERDICTS = ("APPROVE", "BLOCK", "NEEDS-HUMAN")
RISK_PREFIXES = {
    "File": ("RISK:",),
    "Wholesale": ("RISK:",),
    "Piece": ("RISK (partial)", "NEEDS-HUMAN"),
    "Contract": ("CONTRACT:",),
}
EXPECTED_KEYS = ("mode", "expected_verdict", "expected_checks", "expected_prescan", "expect_json", "notes")
RESERVED_FILES = frozenset({"expected.json", "context.md"})
DEFAULT_CASES = REPO_ROOT / "eval" / "cases"
DEFAULT_POLICIES = (REPO_ROOT / "TIME.md", REPO_ROOT / "SYNC.md")

ModelCall = Callable[[str, str, str], str]


@dataclass(frozen=True)
class Case:
    """One golden corpus case."""

    slug: str
    expected: dict
    files: dict[str, str]
    context: str


def load_case(case_dir: Path) -> Case:
    """Return the case stored in one directory."""
    expected = json.loads((case_dir / "expected.json").read_text(encoding="utf-8"))
    context_path = case_dir / "context.md"
    context = context_path.read_text(encoding="utf-8") if context_path.is_file() else ""
    files = {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(case_dir.iterdir())
        if path.is_file() and path.name not in RESERVED_FILES
    }
    return Case(case_dir.name, expected, files, context)


def verdict_fits_mode(mode: str, verdict: str) -> bool:
    """Return True when the expected verdict matches the mode's final line."""
    if mode == "PR":
        return verdict in PR_VERDICTS
    return verdict.startswith(RISK_PREFIXES.get(mode, ()))


def validate_expected(case: Case, known_checks: set[str]) -> list[str]:
    """Return structure problems for one case's expected.json."""
    expected = case.expected
    problems = [f"missing key '{key}'" for key in EXPECTED_KEYS if key not in expected]
    if problems:
        return problems
    mode, verdict = expected["mode"], expected["expected_verdict"]
    if mode not in MODES:
        return [f"invalid mode '{mode}'"]
    if not verdict_fits_mode(mode, verdict):
        problems.append(f"verdict '{verdict}' does not fit mode {mode}")
    for key in ("expected_checks", "expected_prescan"):
        problems.extend(f"unknown check '{item}' in {key}" for item in expected[key] if item not in known_checks)
    if mode == "PR" and expected["expected_prescan"]:
        problems.append("PR cases carry no head tree, so expected_prescan must be empty")
    if not isinstance(expected["expect_json"], bool):
        problems.append("expect_json must be a boolean")
    if not isinstance(expected["notes"], str) or not expected["notes"].strip():
        problems.append("notes must be a non-empty string")
    return problems


def scanned_names(case: Case) -> list[str]:
    """Return fixture names the scanners read: input.<ext> files and named configuration files."""
    return [name for name in case.files if name.startswith("input.") or name in time_checks.common.CONFIG_NAMES]


def validate_fixtures(case: Case) -> list[str]:
    """Return fixture problems for one case."""
    if case.expected.get("mode") == "PR":
        return [] if "diff.patch" in case.files else ["PR mode requires diff.patch"]
    return [] if scanned_names(case) else ["non-PR mode requires an input.<ext> file or a named config file"]


def load_known_checks(policy_paths: tuple[Path, ...]) -> set[str]:
    """Return every check ID listed in the policy documents."""
    known: set[str] = set()
    for path in policy_paths:
        known.update(check_doc_policy.parse_checks(path.read_text(encoding="ascii")))
    return known


def prescan_problems(case: Case, case_dir: Path) -> list[str]:
    """Return differences between scanner check IDs and expected_prescan."""
    found = {item["check"] for item in prescan_for(case, case_dir)}
    expected = set(case.expected["expected_prescan"])
    problems = [f"scanner missed expected check {item}" for item in sorted(expected - found)]
    return problems + [f"scanner reported unexpected check {item}" for item in sorted(found - expected)]


def validate_corpus(cases_dir: Path, policy_paths: tuple[Path, ...] = DEFAULT_POLICIES) -> list[str]:
    """Return every structure and prescan problem across the corpus."""
    known_checks = load_known_checks(policy_paths)
    problems: list[str] = []
    case_dirs = sorted(path for path in cases_dir.iterdir() if path.is_dir())
    if not case_dirs:
        return [f"no cases under {cases_dir}"]
    for case_dir in case_dirs:
        if not (case_dir / "expected.json").is_file():
            problems.append(f"{case_dir.name}: missing expected.json")
            continue
        try:
            case = load_case(case_dir)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            problems.append(f"{case_dir.name}: unreadable case: {error}")
            continue
        issues = validate_expected(case, known_checks) + validate_fixtures(case)
        if not issues:
            issues = prescan_problems(case, case_dir)
        problems.extend(f"{case.slug}: {issue}" for issue in issues)
    return problems


def prescan_for(case: Case, case_dir: Path) -> list[dict]:
    """Return checker candidates for non-PR input files. PR cases carry no head tree."""
    if case.expected["mode"] == "PR":
        return []
    inputs = [case_dir / name for name in scanned_names(case)]
    findings = time_checks.run_checks(list(time_checks.CHECKS), inputs, case_dir)
    return time_checks.prescan_entries(findings, time_checks.load_methods())


def build_case_text(case: Case, case_dir: Path) -> str:
    """Return the review envelope for one case."""
    metadata = {"source": "eval", "case": case.slug}
    prescan = prescan_for(case, case_dir)
    return review_envelope.build_envelope(case.expected["mode"], case.files, case.context, prescan, metadata)


def evaluate_response(case: Case, response: str) -> list[str]:
    """Return mismatches between a model report and the case expectation."""
    report = review_report.parse_report(response)
    expected = case.expected
    failures = []
    final_line = f"{report.label}: {report.value}" if report.label else ""
    if expected["expected_verdict"] not in final_line:
        failures.append(f"expected verdict '{expected['expected_verdict']}' in final line '{final_line}'")
    if expected["expect_json"] and report.payload is None:
        failures.append(report.json_error or "missing VERDICT_JSON")
    if report.payload is not None:
        entries = [*report.payload.get("findings", []), *report.payload.get("escalations", [])]
        reported = {item.get("check") for item in entries if isinstance(item, dict)}
        failures.extend(
            f"missing expected check {item}" for item in expected["expected_checks"] if item not in reported
        )
    return failures


def load_model_call(spec: str) -> ModelCall:
    """Import module:function from a trusted specification."""
    module_name, _, function_name = spec.partition(":")
    if not module_name or not function_name:
        raise ValueError(f"--model-call must look like module:function, got '{spec}'")
    sys.path.insert(0, str(REPO_ROOT))
    return getattr(importlib.import_module(module_name), function_name)


def run_live(cases_dir: Path, policy_paths: tuple[Path, ...], model_call: ModelCall) -> int:
    """Run every case through the model and return the failure count."""
    system_prompt = "\n\n".join(path.read_text(encoding="ascii") for path in policy_paths)
    failures = 0
    for case_dir in sorted(path for path in cases_dir.iterdir() if path.is_dir()):
        case = load_case(case_dir)
        response = model_call(system_prompt, case.expected["mode"], build_case_text(case, case_dir))
        problems = evaluate_response(case, response)
        status = "FAIL" if problems else "pass"
        sys.stdout.write(f"{status:4} {case.slug}\n")
        for problem in problems:
            sys.stdout.write(f"       {problem}\n")
        failures += bool(problems)
    return failures


def main() -> int:
    """Validate the corpus and optionally run it live."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--policy", type=Path, action="append", help="policy document; repeatable")
    parser.add_argument("--model-call", help="trusted module:function for a live run")
    args = parser.parse_args()
    policies = tuple(args.policy) if args.policy else DEFAULT_POLICIES
    problems = validate_corpus(args.cases, policies)
    for problem in problems:
        sys.stderr.write(f"error: {problem}\n")
    if problems:
        return 1
    case_count = sum(1 for path in args.cases.iterdir() if path.is_dir())
    sys.stdout.write(f"ok       {case_count} cases, structure and prescan valid\n")
    if not args.model_call:
        return 0
    failures = run_live(args.cases, policies, load_model_call(args.model_call))
    sys.stdout.write(f"{case_count - failures}/{case_count} cases passed\n")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate a model review report against TIME.md, SYNC.md, and the envelope.

A report passes only with one final line of the right kind for its mode, a
matching VERDICT_JSON, known checks with their policy method tags, valid
severities, a verdict consistent with the severity rule, changed-file
locations, named escalations, and a resolution for every prescan item.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_doc_policy  # resolved through the path set above
import review_report  # resolved through the path set above

SCHEMA_VERSION = "1"
DEFAULT_POLICIES = (REPO_ROOT / "TIME.md", REPO_ROOT / "SYNC.md")
SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
BLOCKING_SEVERITIES = frozenset({"CRITICAL", "HIGH"})
CONFIDENCES = ("certain", "likely")
PRESCAN_STATUSES = ("confirmed", "dismissed")
VERDICT_RANK = {"APPROVE": 0, "NEEDS-HUMAN": 1, "BLOCK": 2}
RISK_TOKENS = frozenset({*SEVERITIES, "NONE-FOUND"})
CONTRACT_TOKENS = frozenset({"COMPLETE", "GAPS", "NEEDS-HUMAN"})
MODE_LINES = {
    "PR": ("VERDICT", frozenset(VERDICT_RANK)),
    "File": ("RISK", RISK_TOKENS),
    "Wholesale": ("RISK", RISK_TOKENS),
    "Piece": ("RISK (partial)", RISK_TOKENS),
    "Contract": ("CONTRACT", CONTRACT_TOKENS),
}


@dataclass(frozen=True)
class ReviewContext:
    """Envelope facts the report must agree with."""

    mode: str
    changed_files: set[str]
    prescan_ids: set[str]
    unreviewed: list[str]


def load_checks(policy_paths: tuple[Path, ...] = DEFAULT_POLICIES) -> dict[str, check_doc_policy.PolicyCheck]:
    """Return the checks of every policy document keyed by check ID."""
    checks: dict[str, check_doc_policy.PolicyCheck] = {}
    for path in policy_paths:
        checks.update(check_doc_policy.parse_checks(path.read_text(encoding="ascii")))
    return checks


def system_prompt(policy_paths: tuple[Path, ...] = DEFAULT_POLICIES) -> str:
    """Return the policy documents joined into one system prompt."""
    return "\n\n".join(path.read_text(encoding="ascii") for path in policy_paths)


def finding_problems(item: object, context: ReviewContext, checks: dict) -> list[str]:
    """Return problems for one VERDICT_JSON finding."""
    if not isinstance(item, dict):
        return ["finding must be a JSON object"]
    problems = []
    check = checks.get(item.get("check"))
    if check is None:
        problems.append(f"unknown check {item.get('check')}")
    elif item.get("method") != check.method:
        problems.append(f"finding for {check.check_id} must carry method {check.method}")
    if item.get("severity") not in SEVERITIES:
        problems.append(f"finding severity must be one of {', '.join(SEVERITIES)}")
    if item.get("confidence") not in CONFIDENCES:
        problems.append("finding confidence must be certain or likely")
    if not isinstance(item.get("line"), int):
        problems.append("finding line must be an integer")
    if context.mode == "PR" and item.get("file") not in context.changed_files:
        problems.append(f"finding cites {item.get('file')} outside the changed files")
    return problems


def escalation_problems(entries: object, checks: dict) -> list[str]:
    """Return problems in the escalations array."""
    if not isinstance(entries, list):
        return ["VERDICT_JSON escalations must be an array"]
    problems = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("check") not in checks or not entry.get("decision"):
            problems.append("escalations need a known check and the missing decision")
    return problems


def required_verdict(findings: list[dict], escalations: list) -> str:
    """Return the verdict the severity rule demands."""
    if any(item.get("severity") in BLOCKING_SEVERITIES for item in findings):
        return "BLOCK"
    return "NEEDS-HUMAN" if escalations else "APPROVE"


def verdict_problems(verdict: str, findings: list[dict], escalations: list, context: ReviewContext) -> list[str]:
    """Return problems where the PR verdict disagrees with the severity rule or coverage."""
    required = required_verdict([item for item in findings if isinstance(item, dict)], escalations)
    if context.unreviewed and verdict == "APPROVE":
        return ["unreviewed files forbid APPROVE"]
    if verdict == required or (verdict == "NEEDS-HUMAN" and required == "APPROVE" and context.unreviewed):
        return []
    return [f"verdict {verdict} conflicts with the severity rule, expected {required}"]


def contract_problems(result: str, findings: list, escalations: list) -> list[str]:
    """Return problems where a CONTRACT result disagrees with its findings and escalations."""
    if result == "COMPLETE" and (findings or escalations):
        return ["CONTRACT COMPLETE cannot carry findings or escalations"]
    if result in {"GAPS", "NEEDS-HUMAN"} and not (findings or escalations):
        return [f"CONTRACT {result} needs at least one finding or escalation"]
    return []


def prescan_problems(entries: object, context: ReviewContext) -> list[str]:
    """Return problems in the prescan resolution array."""
    if not isinstance(entries, list):
        return ["VERDICT_JSON prescan must be an array"]
    resolved = set()
    problems = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("status") not in PRESCAN_STATUSES or not entry.get("reason"):
            problems.append("prescan entries need an id, a confirmed or dismissed status, and a reason")
            continue
        resolved.add(entry.get("id"))
    problems.extend(f"prescan item {item} lacks a resolution" for item in sorted(context.prescan_ids - resolved))
    return problems


def final_line_problems(report: review_report.ParsedReport, mode: str) -> list[str]:
    """Return problems with the final line for the review mode."""
    label, tokens = MODE_LINES[mode]
    if report.label != label:
        return [f"expected exactly one final {label} line, found {report.label or 'none'}"]
    if report.final_line_count != 1:
        return [f"expected exactly one final {label} line, found {report.final_line_count}"]
    if report.token not in tokens:
        return [f"unknown {label} token {report.token}"]
    return []


def payload_problems(payload: dict, report: review_report.ParsedReport, context: ReviewContext) -> list[str]:
    """Return problems in the VERDICT_JSON header fields."""
    problems = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"VERDICT_JSON schema_version must be '{SCHEMA_VERSION}'")
    if payload.get("mode") != context.mode:
        problems.append(f"VERDICT_JSON mode '{payload.get('mode')}' differs from envelope mode '{context.mode}'")
    if payload.get("verdict") != report.token:
        problems.append(f"VERDICT_JSON verdict '{payload.get('verdict')}' differs from final line '{report.token}'")
    return problems


def validate(text: str, context: ReviewContext, checks: dict) -> list[str]:
    """Return every problem in one report. An empty list means valid."""
    if context.mode not in MODE_LINES:
        return [f"unknown review mode {context.mode}"]
    report = review_report.parse_report(text)
    problems = final_line_problems(report, context.mode)
    if report.payload is None:
        return problems + [report.json_error or "missing VERDICT_JSON"]
    payload = report.payload
    problems.extend(payload_problems(payload, report, context))
    findings, escalations = payload.get("findings"), payload.get("escalations", [])
    if not isinstance(findings, list):
        return problems + ["VERDICT_JSON findings must be an array"]
    for item in findings:
        problems.extend(finding_problems(item, context, checks))
    problems.extend(escalation_problems(escalations, checks))
    if not isinstance(escalations, list):
        escalations = []
    if context.mode == "PR" and report.token in VERDICT_RANK:
        problems.extend(verdict_problems(report.token, findings, escalations, context))
    if context.mode == "Contract" and report.token in CONTRACT_TOKENS:
        problems.extend(contract_problems(report.token, findings, escalations))
    problems.extend(prescan_problems(payload.get("prescan", []), context))
    return problems


def context_from_envelope(envelope: dict, unreviewed: list[str]) -> ReviewContext:
    """Return the validation context for one envelope."""
    target = envelope["REVIEW_TARGET"]
    prescan = envelope["TRUSTED_CONTEXT"].get("prescan", [])
    return ReviewContext(envelope["mode"], set(target["files"]), {item["id"] for item in prescan}, unreviewed)


def main() -> int:
    """Validate one report file against one envelope file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("envelope", type=Path)
    parser.add_argument("--policy", type=Path, action="append", help="policy document; repeatable")
    args = parser.parse_args()
    policies = tuple(args.policy) if args.policy else DEFAULT_POLICIES
    envelope = json.loads(args.envelope.read_text(encoding="utf-8"))
    context = context_from_envelope(envelope, [])
    problems = validate(args.report.read_text(encoding="utf-8"), context, load_checks(policies))
    for problem in problems:
        sys.stderr.write(f"error: {problem}\n")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

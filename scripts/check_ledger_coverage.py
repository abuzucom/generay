#!/usr/bin/env python3
"""Check that the problem ledger, class drafts, and review prompts agree.

Rules (Rule 13 check, approved by the maintainer):
- Every PA in docs/problems.md and every BP in docs/best-practices.md has
  exactly one ledger entry, and the ledger lists nothing else.
- Every check the ledger references exists in data/ledger.json "checks",
  and every ledger check appears in its class file under docs/classes/.
- Every ledger check is referenced by at least one PA or BP.
- TIME.md and SYNC.md together list every ledger check exactly once, with
  the method tag the ledger records.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_doc_policy import parse_checks  # resolved through the path set above

REPO_ROOT = Path(__file__).resolve().parent.parent
PA_HEADING = re.compile(r"^- (PA-\d+):", re.MULTILINE)
BP_HEADING = re.compile(r"^- (BP-\d+):", re.MULTILINE)
CLASS_CHECK = re.compile(r"^- (C\d+\.\d+) ", re.MULTILINE)
POLICY_ENTRY = re.compile(r"^(?:\| |### )(C\d+\.\d+) ", re.MULTILINE)


def find_id_violations(kind: str, documented: list[str], ledgered: set[str]) -> list[str]:
    """Return IDs documented twice, missing from the ledger, or ledgered without a note."""
    violations = [f"{kind} documented more than once: {item}" for item, n in Counter(documented).items() if n > 1]
    violations += [f"{kind} missing from the ledger: {item}" for item in sorted(set(documented) - ledgered)]
    violations += [f"{kind} in the ledger without a note: {item}" for item in sorted(ledgered - set(documented))]
    return violations


def find_reference_violations(ledger: dict) -> list[str]:
    """Return unknown check references and checks no PA or BP references."""
    checks = ledger["checks"]
    violations = []
    referenced: set[str] = set()
    for source in ("problems", "best_practices"):
        for item_id, entry in ledger[source].items():
            for check_id in entry["checks"]:
                if check_id not in checks:
                    violations.append(f"{item_id} references unknown check {check_id}")
                referenced.add(check_id)
    violations += [f"check referenced by no PA or BP: {check_id}" for check_id in sorted(set(checks) - referenced)]
    return violations


def find_class_file_violations(ledger: dict, root: Path) -> list[str]:
    """Return ledger checks absent from their class file, and class-file checks absent from the ledger."""
    violations = []
    for class_id, entry in ledger["classes"].items():
        path = root / entry["file"]
        if not path.is_file():
            violations.append(f"missing class file for {class_id}: {entry['file']}")
            continue
        drafted = set(CLASS_CHECK.findall(path.read_text(encoding="utf-8")))
        expected = {check_id for check_id, check in ledger["checks"].items() if check["class"] == class_id}
        violations += [f"{check_id} missing from {entry['file']}" for check_id in sorted(expected - drafted)]
        violations += [
            f"{check_id} in {entry['file']} but not in the ledger" for check_id in sorted(drafted - expected)
        ]
    return violations


def find_policy_violations(ledger: dict, policy_texts: dict[str, str]) -> list[str]:
    """Return checks missing from, duplicated in, or mis-tagged in the review prompts."""
    listed: Counter[str] = Counter()
    parsed = {}
    for text in policy_texts.values():
        listed.update(POLICY_ENTRY.findall(text))
        parsed.update(parse_checks(text))
    violations = [f"check listed more than once in the prompts: {check_id}" for check_id, n in listed.items() if n > 1]
    for check_id, entry in ledger["checks"].items():
        if check_id not in listed:
            violations.append(f"check missing from TIME.md and SYNC.md: {check_id}")
        elif check_id in parsed and parsed[check_id].method != entry["method"]:
            violations.append(
                f"method mismatch for {check_id}: prompt {parsed[check_id].method}, ledger {entry['method']}"
            )
    violations += [
        f"prompt lists a check not in the ledger: {check_id}"
        for check_id in sorted(set(listed) - set(ledger["checks"]))
    ]
    return violations


def find_violations(root: Path) -> list[str]:
    """Return every coverage violation for the repository at root."""
    ledger = json.loads((root / "data" / "ledger.json").read_text(encoding="utf-8"))
    problems = PA_HEADING.findall((root / "docs" / "problems.md").read_text(encoding="utf-8"))
    practices = BP_HEADING.findall((root / "docs" / "best-practices.md").read_text(encoding="utf-8"))
    policy_texts = {name: (root / name).read_text(encoding="utf-8") for name in ("TIME.md", "SYNC.md")}
    violations = find_id_violations("PA", problems, set(ledger["problems"]))
    violations += find_id_violations("BP", practices, set(ledger["best_practices"]))
    violations += find_reference_violations(ledger)
    violations += find_class_file_violations(ledger, root)
    violations += find_policy_violations(ledger, policy_texts)
    return violations


def main() -> int:
    """Print violations and return a blocking exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    args = parser.parse_args()
    violations = find_violations(args.root)
    for violation in violations:
        print(f"error: {violation}", file=sys.stderr)
    if violations:
        return 1
    print("ok       ledger coverage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Tests for scripts/check_ledger_coverage.py."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_ledger_coverage as coverage  # resolved through the path set above


def small_ledger() -> dict:
    """Return a two-check ledger."""
    return {
        "classes": {"C1": {"title": "t", "file": "docs/classes/c1.md"}},
        "checks": {
            "C1.1": {"title": "a", "class": "C1", "method": "both"},
            "C1.2": {"title": "b", "class": "C1", "method": "llm"},
        },
        "problems": {"PA-1": {"primary_class": "C1", "checks": ["C1.1"]}},
        "best_practices": {"BP-1": {"checks": ["C1.2"]}},
    }


class IdTest(unittest.TestCase):
    def test_missing_from_ledger(self) -> None:
        self.assertEqual(
            coverage.find_id_violations("PA", ["PA-1", "PA-2"], {"PA-1"}), ["PA missing from the ledger: PA-2"]
        )

    def test_ledger_entry_without_note(self) -> None:
        self.assertEqual(
            coverage.find_id_violations("PA", ["PA-1"], {"PA-1", "PA-3"}), ["PA in the ledger without a note: PA-3"]
        )

    def test_duplicate_note(self) -> None:
        self.assertEqual(
            coverage.find_id_violations("BP", ["BP-1", "BP-1"], {"BP-1"}), ["BP documented more than once: BP-1"]
        )


class ReferenceTest(unittest.TestCase):
    def test_clean_ledger(self) -> None:
        self.assertEqual(coverage.find_reference_violations(small_ledger()), [])

    def test_unknown_check_reference(self) -> None:
        ledger = small_ledger()
        ledger["problems"]["PA-1"]["checks"].append("C9.9")
        self.assertIn("PA-1 references unknown check C9.9", coverage.find_reference_violations(ledger))

    def test_unreferenced_check(self) -> None:
        ledger = small_ledger()
        ledger["best_practices"]["BP-1"]["checks"] = []
        self.assertIn("check referenced by no PA or BP: C1.2", coverage.find_reference_violations(ledger))


class PolicyTest(unittest.TestCase):
    TEXT = "| C1.1 | both | a | f | n |\n| C1.2 | llm | b | f | n |\n"

    def test_matching_prompts(self) -> None:
        self.assertEqual(coverage.find_policy_violations(small_ledger(), {"TIME.md": self.TEXT}), [])

    def test_missing_check(self) -> None:
        text = "| C1.1 | both | a | f | n |\n"
        self.assertIn(
            "check missing from TIME.md and SYNC.md: C1.2",
            coverage.find_policy_violations(small_ledger(), {"TIME.md": text}),
        )

    def test_method_mismatch(self) -> None:
        text = self.TEXT.replace("| llm |", "| both |")
        violations = coverage.find_policy_violations(small_ledger(), {"TIME.md": text})
        self.assertIn("method mismatch for C1.2: prompt both, ledger llm", violations)

    def test_check_in_both_documents(self) -> None:
        violations = coverage.find_policy_violations(
            small_ledger(), {"TIME.md": self.TEXT, "SYNC.md": "### C1.1 a (both)\n"}
        )
        self.assertIn("check listed more than once in the prompts: C1.1", violations)

    def test_unknown_check_in_prompt(self) -> None:
        text = self.TEXT + "| C2.1 | both | c | f | n |\n"
        self.assertIn(
            "prompt lists a check not in the ledger: C2.1",
            coverage.find_policy_violations(small_ledger(), {"TIME.md": text}),
        )


class ClassFileTest(unittest.TestCase):
    def test_missing_file(self) -> None:
        violations = coverage.find_class_file_violations(small_ledger(), REPO_ROOT / "nowhere")
        self.assertEqual(violations, ["missing class file for C1: docs/classes/c1.md"])


class RepositoryTest(unittest.TestCase):
    def test_repository_is_covered(self) -> None:
        self.assertEqual(coverage.find_violations(REPO_ROOT), [])

    def test_ledger_has_expected_size(self) -> None:
        ledger = json.loads((REPO_ROOT / "data" / "ledger.json").read_text(encoding="utf-8"))
        self.assertEqual(len(ledger["classes"]), 27)
        self.assertEqual(len(ledger["checks"]), 159)
        self.assertEqual(len(ledger["problems"]), 155)

    def test_dropping_every_reference_is_detected(self) -> None:
        ledger = copy.deepcopy(json.loads((REPO_ROOT / "data" / "ledger.json").read_text(encoding="utf-8")))
        for source in ("problems", "best_practices"):
            for entry in ledger[source].values():
                if "C27.7" in entry["checks"]:
                    entry["checks"].remove("C27.7")
        self.assertIn("check referenced by no PA or BP: C27.7", coverage.find_reference_violations(ledger))


if __name__ == "__main__":
    unittest.main()

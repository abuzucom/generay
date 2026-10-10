"""Tests for eval/run_eval.py and scripts/review_report.py."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "eval"))

import review_report  # resolved through the path set above
import run_eval  # resolved through the path set above

GOOD_PR_RESPONSE = """[HIGH] app.py:3 - Swallowed error
  Check: C7.1.

VERDICT: BLOCK - C7.1 elapsed versus calendar meaning.
VERDICT_JSON: {"schema_version": "1", "mode": "PR", "verdict": "BLOCK", "findings": [{"severity": "HIGH", "check": "C7.1", "method": "both", "file": "app.py", "line": 3, "title": "Swallowed error", "confidence": "certain"}], "escalations": [], "prescan": []}
"""


class CaseFixture(unittest.TestCase):
    """Base case building a temporary corpus."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.cases = Path(self.temp_dir.name)

    def write_case(self, slug: str, expected: dict, files: dict[str, str]) -> Path:
        """Write one case directory."""
        case_dir = self.cases / slug
        case_dir.mkdir()
        (case_dir / "expected.json").write_text(json.dumps(expected), encoding="utf-8")
        for name, content in files.items():
            (case_dir / name).write_text(content, encoding="utf-8")
        return case_dir

    def valid_expected(self, **overrides: object) -> dict:
        """Return a valid PR expectation with overrides applied."""
        expected = {
            "mode": "PR",
            "expected_verdict": "BLOCK",
            "expected_checks": ["C7.1"],
            "expected_prescan": [],
            "expect_json": True,
            "notes": "The handler swallows the error.",
        }
        expected.update(overrides)
        return expected


class StructureTest(CaseFixture):
    def test_repository_corpus_is_valid(self) -> None:
        self.assertEqual(run_eval.validate_corpus(REPO_ROOT / "eval" / "cases"), [])

    def test_valid_case_passes(self) -> None:
        self.write_case("ok-pr", self.valid_expected(), {"diff.patch": "--- a/x\n+++ b/x\n"})
        self.assertEqual(run_eval.validate_corpus(self.cases), [])

    def test_bad_mode_fails(self) -> None:
        self.write_case("bad-mode", self.valid_expected(mode="Diff"), {"diff.patch": ""})
        self.assertIn("bad-mode: invalid mode 'Diff'", run_eval.validate_corpus(self.cases))

    def test_unknown_check_fails(self) -> None:
        self.write_case("bad-check", self.valid_expected(expected_checks=["C99.9"]), {"diff.patch": ""})
        self.assertIn("bad-check: unknown check 'C99.9' in expected_checks", run_eval.validate_corpus(self.cases))

    def test_missing_fixture_fails(self) -> None:
        self.write_case("no-diff", self.valid_expected(), {})
        self.assertIn("no-diff: PR mode requires diff.patch", run_eval.validate_corpus(self.cases))

    def test_verdict_mode_mismatch_fails(self) -> None:
        self.write_case("mismatch", self.valid_expected(expected_verdict="RISK: HIGH"), {"diff.patch": ""})
        self.assertIn("mismatch: verdict 'RISK: HIGH' does not fit mode PR", run_eval.validate_corpus(self.cases))

    def test_empty_notes_fail(self) -> None:
        self.write_case("no-notes", self.valid_expected(notes=""), {"diff.patch": ""})
        self.assertIn("no-notes: notes must be a non-empty string", run_eval.validate_corpus(self.cases))

    def test_pr_case_with_expected_prescan_fails(self) -> None:
        self.write_case("pr-prescan", self.valid_expected(expected_prescan=["C1.2"]), {"diff.patch": ""})
        problems = run_eval.validate_corpus(self.cases)
        self.assertIn("pr-prescan: PR cases carry no head tree, so expected_prescan must be empty", problems)

    def test_contract_case_valid(self) -> None:
        expected = self.valid_expected(mode="Contract", expected_verdict="CONTRACT: GAPS", expected_checks=["C26.1"])
        self.write_case("contract", expected, {"input.md": "Due 2026-10-10 17:00.\n"})
        self.assertEqual(run_eval.validate_corpus(self.cases), [])

    def test_scanner_difference_fails(self) -> None:
        expected = self.valid_expected(mode="File", expected_verdict="RISK: HIGH", expected_prescan=["C7.1"])
        self.write_case("scan-miss", expected, {"input.py": "DAY = 86400\n"})
        problems = run_eval.validate_corpus(self.cases)
        self.assertIn("scan-miss: scanner missed expected check C7.1", problems)
        self.assertIn("scan-miss: scanner reported unexpected check C1.2", problems)

    def test_named_config_file_is_scanned(self) -> None:
        expected = self.valid_expected(mode="File", expected_verdict="RISK: MEDIUM", expected_prescan=["C27.2"])
        self.write_case("named-config", expected, {"chrony.conf": "server a.example\nserver b.example\nrtcsync\n"})
        problems = run_eval.validate_corpus(self.cases)
        self.assertNotIn("named-config: scanner missed expected check C27.2", problems)


class ReportParsingTest(unittest.TestCase):
    def test_parses_final_line_and_json(self) -> None:
        report = review_report.parse_report(GOOD_PR_RESPONSE)
        self.assertEqual(report.label, "VERDICT")
        self.assertEqual(report.token, "BLOCK")
        self.assertEqual(report.payload["findings"][0]["check"], "C7.1")

    def test_missing_final_line(self) -> None:
        report = review_report.parse_report("no verdict here")
        self.assertIsNone(report.label)
        self.assertIsNone(report.payload)

    def test_contract_label(self) -> None:
        report = review_report.parse_report("CONTRACT: GAPS - no zone stated\n")
        self.assertEqual(report.label, "CONTRACT")
        self.assertEqual(report.token, "GAPS")

    def test_risk_partial_label(self) -> None:
        report = review_report.parse_report("RISK (partial): MEDIUM - unseen caller\n")
        self.assertEqual(report.label, "RISK (partial)")
        self.assertEqual(report.token, "MEDIUM")


class LiveEvaluationTest(CaseFixture):
    def test_matching_response_passes(self) -> None:
        case_dir = self.write_case("ok-pr", self.valid_expected(), {"diff.patch": "+x\n"})
        case = run_eval.load_case(case_dir)
        self.assertEqual(run_eval.evaluate_response(case, GOOD_PR_RESPONSE), [])

    def test_wrong_verdict_fails(self) -> None:
        case_dir = self.write_case("ok-pr", self.valid_expected(expected_verdict="APPROVE"), {"diff.patch": "+x\n"})
        failures = run_eval.evaluate_response(run_eval.load_case(case_dir), GOOD_PR_RESPONSE)
        self.assertTrue(any("expected verdict 'APPROVE'" in item for item in failures))

    def test_missing_check_fails(self) -> None:
        case_dir = self.write_case("ok-pr", self.valid_expected(expected_checks=["C14.6"]), {"diff.patch": "+x\n"})
        failures = run_eval.evaluate_response(run_eval.load_case(case_dir), GOOD_PR_RESPONSE)
        self.assertIn("missing expected check C14.6", failures)

    def test_case_text_is_json_envelope(self) -> None:
        files = {"diff.patch": "+x\n", "context.md": "Adds a handler."}
        case = run_eval.load_case(self.write_case("ok-pr", self.valid_expected(), files))
        envelope = json.loads(run_eval.build_case_text(case, self.cases / "ok-pr"))
        self.assertEqual(envelope["mode"], "PR")
        self.assertEqual(envelope["REVIEW_TARGET"]["files"]["diff.patch"], "+x\n")
        self.assertEqual(envelope["REVIEW_TARGET"]["context"], "Adds a handler.")
        self.assertIn("sha256", envelope["REVIEW_TARGET"])


if __name__ == "__main__":
    unittest.main()

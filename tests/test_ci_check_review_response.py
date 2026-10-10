"""Tests for ci/check_review_response.py."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ci import check_review_response as checker  # resolved through the path set above

METHOD_OF = {"C7.1": "both", "C2.1": "heuristic", "C14.6": "llm", "C27.7": "both", "C26.1": "llm"}


def build_report(
    verdict: str,
    findings: list[dict],
    prescan: list[dict] | None = None,
    escalations: list[dict] | None = None,
    mode: str = "PR",
    label: str = "VERDICT",
    **overrides: object,
) -> str:
    """Return a report with a final line and a VERDICT_JSON companion."""
    payload = {
        "schema_version": "1",
        "mode": mode,
        "verdict": verdict,
        "findings": findings,
        "escalations": escalations or [],
        "prescan": prescan or [],
    }
    payload.update(overrides)
    return f"Findings above.\n\n{label}: {verdict} - summary\nVERDICT_JSON: {json.dumps(payload)}\n"


def finding(check: str, severity: str = "HIGH", file: str = "app.py") -> dict:
    """Return one finding entry with the check's own method tag."""
    return {
        "severity": severity,
        "check": check,
        "method": METHOD_OF.get(check, "both"),
        "file": file,
        "line": 3,
        "title": "t",
        "confidence": "certain",
    }


class ValidateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.checks = checker.load_checks()
        self.context = checker.ReviewContext("PR", {"app.py"}, {"P1"}, [])

    def problems(self, report: str, context: checker.ReviewContext | None = None) -> list[str]:
        return checker.validate(report, context or self.context, self.checks)

    def dismissed(self) -> list[dict]:
        return [{"id": "P1", "status": "dismissed", "reason": "value clear from context"}]

    def test_policy_methods_match_fixture_table(self) -> None:
        for check_id, method in METHOD_OF.items():
            self.assertEqual(self.checks[check_id].method, method)

    def test_valid_block_report(self) -> None:
        self.assertEqual(self.problems(build_report("BLOCK", [finding("C7.1")], self.dismissed())), [])

    def test_valid_clean_approve(self) -> None:
        self.assertEqual(self.problems(build_report("APPROVE", [], self.dismissed())), [])

    def test_critical_finding_requires_block(self) -> None:
        problems = self.problems(build_report("APPROVE", [finding("C27.7", "CRITICAL")], self.dismissed()))
        self.assertIn("verdict APPROVE conflicts with the severity rule, expected BLOCK", problems)

    def test_high_finding_requires_block(self) -> None:
        problems = self.problems(build_report("NEEDS-HUMAN", [finding("C7.1")], self.dismissed()))
        self.assertIn("verdict NEEDS-HUMAN conflicts with the severity rule, expected BLOCK", problems)

    def test_escalation_requires_needs_human(self) -> None:
        escalation = [{"check": "C14.6", "decision": "which zone governs the cutoff"}]
        problems = self.problems(build_report("APPROVE", [], self.dismissed(), escalation))
        self.assertIn("verdict APPROVE conflicts with the severity rule, expected NEEDS-HUMAN", problems)

    def test_escalation_with_needs_human_passes(self) -> None:
        escalation = [{"check": "C14.6", "decision": "which zone governs the cutoff"}]
        self.assertEqual(self.problems(build_report("NEEDS-HUMAN", [], self.dismissed(), escalation)), [])

    def test_medium_finding_allows_approve(self) -> None:
        self.assertEqual(self.problems(build_report("APPROVE", [finding("C7.1", "MEDIUM")], self.dismissed())), [])

    def test_block_without_basis_rejected(self) -> None:
        problems = self.problems(build_report("BLOCK", [finding("C7.1", "LOW")], self.dismissed()))
        self.assertIn("verdict BLOCK conflicts with the severity rule, expected APPROVE", problems)

    def test_two_final_lines_rejected(self) -> None:
        report = "VERDICT: APPROVE - a\n" + build_report("APPROVE", [], self.dismissed())
        self.assertIn("expected exactly one final VERDICT line, found 2", self.problems(report))

    def test_json_verdict_mismatch_rejected(self) -> None:
        report = build_report("APPROVE", [], self.dismissed()).replace('"verdict": "APPROVE"', '"verdict": "BLOCK"')
        self.assertIn("VERDICT_JSON verdict 'BLOCK' differs from final line 'APPROVE'", self.problems(report))

    def test_mode_mismatch_rejected(self) -> None:
        report = build_report("APPROVE", [], self.dismissed(), mode="File")
        self.assertIn("VERDICT_JSON mode 'File' differs from envelope mode 'PR'", self.problems(report))

    def test_file_outside_diff_rejected(self) -> None:
        problems = self.problems(build_report("BLOCK", [finding("C7.1", file="other.py")], self.dismissed()))
        self.assertIn("finding cites other.py outside the changed files", problems)

    def test_unknown_check_rejected(self) -> None:
        problems = self.problems(build_report("APPROVE", [finding("C99.9", "LOW")], self.dismissed()))
        self.assertIn("unknown check C99.9", problems)

    def test_wrong_method_rejected(self) -> None:
        entry = finding("C7.1")
        entry["method"] = "llm"
        problems = self.problems(build_report("BLOCK", [entry], self.dismissed()))
        self.assertIn("finding for C7.1 must carry method both", problems)

    def test_unknown_severity_rejected(self) -> None:
        problems = self.problems(build_report("APPROVE", [finding("C7.1", "SEVERE")], self.dismissed()))
        self.assertIn("finding severity must be one of CRITICAL, HIGH, MEDIUM, LOW", problems)

    def test_missing_confidence_rejected(self) -> None:
        entry = finding("C7.1")
        del entry["confidence"]
        self.assertIn(
            "finding confidence must be certain or likely",
            self.problems(build_report("BLOCK", [entry], self.dismissed())),
        )

    def test_escalation_needs_known_check_and_decision(self) -> None:
        escalation = [{"check": "C14.6", "decision": ""}]
        problems = self.problems(build_report("NEEDS-HUMAN", [], self.dismissed(), escalation))
        self.assertIn("escalations need a known check and the missing decision", problems)

    def test_schema_version_required(self) -> None:
        report = build_report("APPROVE", [], self.dismissed(), schema_version="2")
        self.assertIn("VERDICT_JSON schema_version must be '1'", self.problems(report))

    def test_unresolved_prescan_rejected(self) -> None:
        self.assertIn("prescan item P1 lacks a resolution", self.problems(build_report("APPROVE", [], [])))

    def test_unreviewed_files_forbid_approve(self) -> None:
        context = checker.ReviewContext("PR", {"app.py"}, set(), ["big.bin"])
        self.assertIn("unreviewed files forbid APPROVE", self.problems(build_report("APPROVE", []), context))


class ModeLineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.checks = checker.load_checks()

    def problems(self, mode: str, report: str) -> list[str]:
        return checker.validate(report, checker.ReviewContext(mode, set(), set(), []), self.checks)

    def test_file_risk_line_passes(self) -> None:
        report = build_report("HIGH", [finding("C7.1")], mode="File", label="RISK")
        self.assertEqual(self.problems("File", report), [])

    def test_file_mode_rejects_verdict_line(self) -> None:
        report = build_report("APPROVE", [], mode="File", label="VERDICT")
        self.assertIn("expected exactly one final RISK line, found VERDICT", self.problems("File", report))

    def test_piece_partial_line_passes(self) -> None:
        report = build_report("MEDIUM", [], mode="Piece", label="RISK (partial)")
        self.assertEqual(self.problems("Piece", report), [])

    def test_contract_complete_passes(self) -> None:
        report = build_report("COMPLETE", [], mode="Contract", label="CONTRACT")
        self.assertEqual(self.problems("Contract", report), [])

    def test_contract_complete_with_gap_rejected(self) -> None:
        escalation = [{"check": "C26.1", "decision": "governing zone"}]
        report = build_report("COMPLETE", [], escalations=escalation, mode="Contract", label="CONTRACT")
        self.assertIn("CONTRACT COMPLETE cannot carry findings or escalations", self.problems("Contract", report))

    def test_contract_gaps_need_content(self) -> None:
        report = build_report("GAPS", [], mode="Contract", label="CONTRACT")
        self.assertIn("CONTRACT GAPS needs at least one finding or escalation", self.problems("Contract", report))

    def test_contract_gaps_with_escalation_pass(self) -> None:
        escalation = [{"check": "C26.1", "decision": "governing zone"}]
        report = build_report("GAPS", [], escalations=escalation, mode="Contract", label="CONTRACT")
        self.assertEqual(self.problems("Contract", report), [])

    def test_unknown_mode_rejected(self) -> None:
        self.assertEqual(self.problems("Audit", "x"), ["unknown review mode Audit"])


if __name__ == "__main__":
    unittest.main()

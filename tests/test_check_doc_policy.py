"""Tests for scripts/check_doc_policy.py."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_doc_policy as policy  # resolved through the path set above


class ParseChecksTest(unittest.TestCase):
    def test_table_row_and_heading_forms(self) -> None:
        text = "| C1.2 | both | Day length | flag | not a finding |\n### C27.7 Public pools (both)\n"
        checks = policy.parse_checks(text)
        self.assertEqual(checks["C1.2"].method, "both")
        self.assertEqual(checks["C27.7"].name, "Public pools")

    def test_invalid_method_not_parsed(self) -> None:
        self.assertEqual(policy.parse_checks("| C1.2 | maybe | Day | f | n |\n"), {})

    def test_invalid_method_reported(self) -> None:
        violations = policy.find_check_violations("| C1.2 | maybe | Day | f | n |\n")
        self.assertEqual(len(violations), 1)
        self.assertIn("without a valid method", violations[0])

    def test_duplicate_reported(self) -> None:
        row = "| C1.2 | both | Day | f | n |\n"
        self.assertIn("duplicate check: C1.2", policy.find_check_violations(row + row))

    def test_missing_cells_reported(self) -> None:
        self.assertEqual(len(policy.find_check_violations("| C1.2 | both | Day | f |\n")), 1)


class ClassCoverageTest(unittest.TestCase):
    def test_time_requires_every_class(self) -> None:
        violations = policy.find_class_violations("### C1 Calendar unit lengths\n| C1.1 | both | h | f | n |\n", "time")
        self.assertIn("missing class heading: C2", violations)
        self.assertIn("class has no checks: C26", violations)

    def test_foreign_check_reported(self) -> None:
        violations = policy.find_class_violations("### C27.1 Sync (both)\n", "time")
        self.assertIn("check belongs to another document: C27.1", violations)

    def test_sync_accepts_c27_only(self) -> None:
        self.assertEqual(policy.find_class_violations("### C27.1 Sync (both)\n", "sync"), [])


class LineRuleTest(unittest.TestCase):
    def test_long_prose_line_reported(self) -> None:
        self.assertEqual(policy.find_line_violations("x" * 121 + "\n"), ["line 1 exceeds 120 characters"])

    def test_table_rows_exempt(self) -> None:
        self.assertEqual(policy.find_line_violations("| " + "x" * 200 + " |\n"), [])

    def test_fenced_lines_exempt(self) -> None:
        self.assertEqual(policy.find_line_violations("```\n" + "x" * 200 + " - y\n```\n"), [])

    def test_spaced_hyphen_reported(self) -> None:
        self.assertEqual(policy.find_line_violations("one - two\n"), ["line 1 uses a prose dash"])

    def test_code_span_dash_allowed(self) -> None:
        self.assertEqual(policy.find_line_violations("use `a - b` here\n"), [])

    def test_bullet_marker_allowed(self) -> None:
        self.assertEqual(policy.find_line_violations("- item\n"), [])


class DecodeTest(unittest.TestCase):
    def test_non_ascii_reported(self) -> None:
        _, violations = policy.decode_policy("café".encode(), limit_size=True)
        self.assertIn("document must contain ASCII text only", violations)

    def test_crlf_reported(self) -> None:
        _, violations = policy.decode_policy(b"a\r\n", limit_size=True)
        self.assertIn("document must use LF line endings", violations)

    def test_size_limit_enforced_only_when_requested(self) -> None:
        raw = b"a" * (policy.MAX_BYTES + 1)
        self.assertEqual(len(policy.decode_policy(raw, limit_size=True)[1]), 1)
        self.assertEqual(policy.decode_policy(raw, limit_size=False)[1], [])


class RepositoryDocumentsTest(unittest.TestCase):
    def test_time_md_valid(self) -> None:
        self.assertEqual(policy.find_violations(REPO_ROOT / "TIME.md"), [])

    def test_sync_md_valid(self) -> None:
        self.assertEqual(policy.find_violations(REPO_ROOT / "SYNC.md"), [])

    def test_kind_from_file_name(self) -> None:
        self.assertEqual(policy.kind_for(Path("SYNC.md")), "sync")
        self.assertEqual(policy.kind_for(Path("TIME.md")), "time")

    def test_missing_document_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = policy.find_violations(Path(temp) / "TIME.md")
        self.assertTrue(result[0].startswith("missing document"))

    def test_both_documents_fit_the_limit(self) -> None:
        for name in ("TIME.md", "SYNC.md"):
            self.assertLessEqual((REPO_ROOT / name).stat().st_size, policy.MAX_BYTES)


if __name__ == "__main__":
    unittest.main()

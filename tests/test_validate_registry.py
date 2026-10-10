"""Tests for scripts/validate_registry.py."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_registry as registry  # resolved through the path set above

SCHEMA = json.loads((REPO_ROOT / "data" / "libraries.schema.json").read_text(encoding="utf-8"))
VALID = json.loads((REPO_ROOT / "data" / "libraries.json").read_text(encoding="utf-8"))


def errors_for(document: object) -> list[str]:
    """Return validation errors for a registry document."""
    return registry.validate(document, SCHEMA, SCHEMA)


class RegistryTest(unittest.TestCase):
    def test_repository_registry_valid(self) -> None:
        self.assertEqual(errors_for(VALID), [])

    def test_missing_required_property(self) -> None:
        document = copy.deepcopy(VALID)
        del document["entries"][0]["preferred"]
        self.assertIn("$.entries[0]: missing preferred", errors_for(document))

    def test_unexpected_property(self) -> None:
        document = copy.deepcopy(VALID)
        document["entries"][0]["favorite"] = True
        self.assertIn("$.entries[0]: unexpected property favorite", errors_for(document))

    def test_bad_repository_pattern(self) -> None:
        document = copy.deepcopy(VALID)
        document["entries"][0]["preferred"]["repository"] = "not a repo"
        self.assertTrue(any("does not match" in item for item in errors_for(document)))

    def test_system_layer_enum(self) -> None:
        document = copy.deepcopy(VALID)
        document["entries"][0]["system_layer"] = ["mainframe"]
        self.assertTrue(any("not in" in item for item in errors_for(document)))

    def test_wrong_type(self) -> None:
        document = copy.deepcopy(VALID)
        document["entries"] = {}
        self.assertIn("$.entries: expected array", errors_for(document))

    def test_boolean_is_not_integer_or_string(self) -> None:
        document = copy.deepcopy(VALID)
        document["entries"][0]["language"] = True
        self.assertIn("$.entries[0].language: expected string", errors_for(document))

    def test_empty_name_rejected(self) -> None:
        document = copy.deepcopy(VALID)
        document["entries"][0]["preferred"]["name"] = ""
        self.assertTrue(any("shorter than" in item for item in errors_for(document)))

    def test_schema_version_enum(self) -> None:
        document = copy.deepcopy(VALID)
        document["schema_version"] = "2"
        self.assertTrue(any("not in" in item for item in errors_for(document)))

    def test_unsupported_keyword_fails_loudly(self) -> None:
        with self.assertRaises(ValueError):
            registry.validate({}, {"oneOf": []}, {})

    def test_external_ref_fails_loudly(self) -> None:
        with self.assertRaises(ValueError):
            registry.validate({}, {"$ref": "http://example.test/x"}, {})


if __name__ == "__main__":
    unittest.main()

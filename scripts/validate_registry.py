#!/usr/bin/env python3
"""Validate data/libraries.json against data/libraries.schema.json.

Uses the standard library only. Supports the JSON Schema subset the
registry schema uses: type, enum, pattern, minLength, required,
properties, additionalProperties (false), items, and local $ref.
Unsupported keywords fail loudly so the schema cannot drift past the
validator silently.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA = REPO_ROOT / "data" / "libraries.schema.json"
DEFAULT_REGISTRY = REPO_ROOT / "data" / "libraries.json"
ANNOTATIONS = frozenset({"$schema", "$id", "$defs", "title", "description"})
SUPPORTED = ANNOTATIONS | {
    "type",
    "enum",
    "pattern",
    "minLength",
    "required",
    "properties",
    "additionalProperties",
    "items",
    "$ref",
}
TYPES: dict[str, type | tuple[type, ...]] = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "integer": int,
    "number": (int, float),
}
REF_PREFIX = "#/$defs/"


def resolve(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    """Return the schema a local $ref points to, or the schema itself."""
    ref = schema.get("$ref")
    if ref is None:
        return schema
    if not ref.startswith(REF_PREFIX):
        raise ValueError(f"unsupported $ref {ref}; use {REF_PREFIX}<name>")
    return root["$defs"][ref.removeprefix(REF_PREFIX)]


def check_scalar(value: Any, schema: dict[str, Any], where: str) -> list[str]:
    """Return type, enum, pattern, and length errors for one value."""
    expected = schema.get("type")
    if expected is not None:
        is_bool = isinstance(value, bool)
        if not isinstance(value, TYPES[expected]) or (is_bool and expected != "boolean"):
            return [f"{where}: expected {expected}"]
    errors = []
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: {value!r} not in {schema['enum']}")
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{where}: {value!r} does not match {schema['pattern']}")
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{where}: shorter than {schema['minLength']}")
    return errors


def check_object(value: dict[str, Any], schema: dict[str, Any], root: dict[str, Any], where: str) -> list[str]:
    """Return errors for required, unknown, and nested properties."""
    properties = schema.get("properties", {})
    errors = [f"{where}: missing {name}" for name in schema.get("required", []) if name not in value]
    if schema.get("additionalProperties") is False:
        errors += [f"{where}: unexpected property {name}" for name in sorted(set(value) - set(properties))]
    for name, child in properties.items():
        if name in value:
            errors += validate(value[name], child, root, f"{where}.{name}")
    return errors


def validate(value: Any, schema: dict[str, Any], root: dict[str, Any], where: str = "$") -> list[str]:
    """Return every error for value against schema."""
    schema = resolve(schema, root)
    unsupported = set(schema) - SUPPORTED
    if unsupported:
        raise ValueError(f"unsupported schema keywords at {where}: {sorted(unsupported)}")
    errors = check_scalar(value, schema, where)
    if errors:
        return errors
    if isinstance(value, dict):
        errors += check_object(value, schema, root, where)
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            errors += validate(item, schema["items"], root, f"{where}[{index}]")
    return errors


def main() -> int:
    """Print validation errors and return a blocking exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args()
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    try:
        errors = validate(registry, schema, schema)
    except ValueError as failure:
        print(f"error: {failure}. Extend scripts/validate_registry.py or simplify the schema.", file=sys.stderr)
        return 2
    for message in errors:
        print(f"error: {args.registry}: {message}", file=sys.stderr)
    if errors:
        return 1
    print(f"ok       {args.registry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

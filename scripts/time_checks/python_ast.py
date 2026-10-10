"""Python syntax-tree time checks.

The checks resolve simple call names (`datetime.now`, `time.time`) without
import tracking. Every hit is a candidate for the model reviewer.
"""

from __future__ import annotations

import ast

from .common import Finding

HOST_ZONE_CALLS = frozenset({
    "datetime.now",
    "datetime.datetime.now",
    "date.today",
    "datetime.date.today",
    "datetime.today",
    "datetime.datetime.today",
    "datetime.utcnow",
    "datetime.datetime.utcnow",
    "datetime.fromtimestamp",
    "datetime.datetime.fromtimestamp",
    "time.mktime",
    "time.localtime",
})
WALL_CLOCK_CALLS = frozenset({"time.time", "time.time_ns"})
SLEEP_CALLS = frozenset({"time.sleep", "sleep"})
SEED_CALLS = frozenset({"random.seed"})
PYTZ_ZONE_CALLS = frozenset({"pytz.timezone", "timezone"})
DATETIME_CONSTRUCTORS = frozenset({"datetime", "datetime.datetime"})


def call_name(node: ast.AST) -> str:
    """Return the dotted name of a call target, or an empty string."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def is_call_to(node: ast.AST, names: frozenset[str]) -> bool:
    """Return True when node is a call to one of the dotted names."""
    return isinstance(node, ast.Call) and call_name(node.func) in names


def host_zone_finding(relative: str, node: ast.Call, name: str) -> Finding | None:
    """C9.1: naive host-zone reads."""
    if name in {"datetime.fromtimestamp", "datetime.datetime.fromtimestamp"}:
        has_zone = len(node.args) > 1 or any(keyword.arg == "tz" for keyword in node.keywords)
        return None if has_zone else Finding(relative, node.lineno, "C9.1", "fromtimestamp without tz", False)
    if name.endswith(".now") and (node.args or node.keywords):
        return None
    return Finding(relative, node.lineno, "C9.1", f"{name}() reads the host zone or returns naive time", False)


def check_calls(relative: str, tree: ast.Module) -> list[Finding]:
    """C9.1, C10.6, C19.5, C21.3: call-site checks."""
    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = call_name(node.func)
        if name in HOST_ZONE_CALLS:
            finding = host_zone_finding(relative, node, name)
            if finding:
                findings.append(finding)
        if name.endswith("astimezone") and not node.args and not node.keywords:
            findings.append(Finding(relative, node.lineno, "C9.1", "astimezone() converts to the host zone", False))
        if name in DATETIME_CONSTRUCTORS:
            for keyword in node.keywords:
                if keyword.arg == "tzinfo" and is_call_to(keyword.value, PYTZ_ZONE_CALLS):
                    findings.append(Finding(relative, node.lineno, "C10.6", "pytz zone passed as tzinfo", False))
        if name in SEED_CALLS and any(is_call_to(arg, WALL_CLOCK_CALLS) for arg in node.args):
            findings.append(Finding(relative, node.lineno, "C19.5", "random generator seeded with the time", False))
        if name in SLEEP_CALLS and node.args and is_negative(node.args[0]):
            findings.append(Finding(relative, node.lineno, "C21.3", "negative sleep duration", False))
    return findings


def is_negative(node: ast.AST) -> bool:
    """Return True for a negative numeric literal."""
    return (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.USub)
        and isinstance(node.operand, ast.Constant)
        and isinstance(node.operand.value, int | float)
    )


def check_wall_clock_durations(relative: str, tree: ast.Module) -> list[Finding]:
    """C18.1: durations from wall-clock subtraction."""
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
            if is_call_to(node.left, WALL_CLOCK_CALLS) or is_call_to(node.right, WALL_CLOCK_CALLS):
                findings.append(Finding(relative, node.lineno, "C18.1", "duration from the wall clock", False))
    return findings


def check_module_scope_now(relative: str, tree: ast.Module) -> list[Finding]:
    """C18.3: "now" captured once at module scope."""
    findings = []
    for statement in tree.body:
        if isinstance(statement, ast.Assign | ast.AnnAssign) and statement.value is not None:
            value = statement.value
            if is_call_to(value, WALL_CLOCK_CALLS | HOST_ZONE_CALLS) or (
                isinstance(value, ast.Call) and call_name(value.func).endswith(".now")
            ):
                findings.append(Finding(relative, statement.lineno, "C18.3", "time read once at module scope", False))
    return findings

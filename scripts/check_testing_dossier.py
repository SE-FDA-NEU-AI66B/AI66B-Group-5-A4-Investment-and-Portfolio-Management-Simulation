"""Resolve every executable pytest mapping in docs/testing.md.

The M4 dossier keeps a table of case IDs and exact pytest nodes. A stale table
would claim evidence that no longer exists, so this audit reads each backticked
``tests/...py::function`` node from section 3, confirms the file and function
exist, and warns when the function name does not carry its TC ID. Rows that are
still planned have no node and are reported as pending, not as failures.
"""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "docs" / "testing.md"
ROW = re.compile(r"^\|\s*(TC-US\d{2}-\d{2})")
NODE = re.compile(r"`(tests/[\w/]+\.py)::(\w+)`")


def functions_in(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def main():
    if not DOSSIER.is_file():
        print(f"Missing dossier: {DOSSIER}")
        return 1

    checked = 0
    failures = []
    warnings = []
    pending = []
    in_section = False

    for number, line in enumerate(DOSSIER.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("## 3. Automated tests"):
            in_section = True
            continue
        if in_section and line.startswith("## 4."):
            break
        if not in_section:
            continue

        case_match = ROW.match(line)
        if not case_match:
            continue
        case = case_match.group(1)
        node_match = NODE.search(line)
        if not node_match:
            pending.append((case, number, line.strip()))
            continue

        relative, function = node_match.groups()
        checked += 1
        source = ROOT / relative
        if not source.is_file():
            failures.append(f"{case}: missing file {relative} (line {number})")
            continue

        if function not in functions_in(source):
            failures.append(
                f"{case}: {relative} has no function {function} (line {number})"
            )
            continue

        expected = case.lower().replace("-", "_")
        if expected not in function:
            warnings.append(
                f"{case}: {function} does not name {case} (line {number})"
            )
        print(f"OK {case} -> {relative}::{function}")

    for warning in warnings:
        print(f"WARN {warning}")
    for failure in failures:
        print(f"FAIL {failure}")
    for case, number, _line in pending:
        print(f"PENDING {case} has no executable node (line {number})")

    print(
        f"\nChecked {checked} executable mappings: "
        f"{checked - len(failures)} resolved, {len(failures)} missing, "
        f"{len(warnings)} warnings, {len(pending)} rows still planned."
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

"""Resolve every executable pytest mapping in docs/testing.md.

The M4 dossier keeps a table of case IDs and exact pytest nodes. A stale table
would claim evidence that no longer exists, so this audit reads every backticked
``tests/...py::function`` node in section 3, including multiple nodes in one
row, confirms the file and function exist, and warns when the primary function
name does not carry its TC ID. A backticked ``::function`` shorthand inherits
the most recent file in the same row, so merged tables that abbreviate later
nodes are still fully checked. Rows that are still planned have no node and are
reported as pending, not as failures.
"""

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "docs" / "testing.md"
ROW = re.compile(r"^\|\s*(TC-US\d{2}-\d{2})")
FULL_NODE = re.compile(r"`(tests/[\w/]+\.py)::(\w+)`")
SHORT_NODE = re.compile(r"`::(\w+)`")


def functions_in(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def nodes_in(line):
    """Return (position, file, function) for each node, expanding shorthand."""
    full = [
        (match.start(), match.group(1), match.group(2))
        for match in FULL_NODE.finditer(line)
    ]
    nodes = list(full)
    for match in SHORT_NODE.finditer(line):
        preceding = [node for node in full if node[0] < match.start()]
        file = preceding[-1][1] if preceding else None
        nodes.append((match.start(), file, match.group(1)))
    return sorted(nodes)


def check(dossier=DOSSIER):
    checked = 0
    failures = []
    warnings = []
    pending = []
    in_section = False

    for number, line in enumerate(dossier.read_text(encoding="utf-8").splitlines(), 1):
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
        nodes = nodes_in(line)
        if not nodes:
            pending.append((case, number, line.strip()))
            continue

        for index, (_position, relative, function) in enumerate(nodes):
            checked += 1
            if relative is None:
                failures.append(
                    f"{case}: `::{function}` has no preceding file path "
                    f"(line {number})"
                )
                continue
            source = ROOT / relative
            if not source.is_file():
                failures.append(
                    f"{case}: missing file {relative} (line {number})"
                )
                continue

            if function not in functions_in(source):
                failures.append(
                    f"{case}: {relative} has no function {function} (line {number})"
                )
                continue

            expected = case.lower().replace("-", "_")
            if index == 0 and expected not in function:
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
        f"\nChecked {checked} executable nodes: "
        f"{checked - len(failures)} resolved, {len(failures)} missing, "
        f"{len(warnings)} warnings, {len(pending)} rows still planned."
    )
    return {
        "checked": checked,
        "failures": failures,
        "warnings": warnings,
        "pending": pending,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dossier",
        type=Path,
        default=DOSSIER,
        help="Path to the testing dossier (default: docs/testing.md).",
    )
    args = parser.parse_args(argv)
    result = check(args.dossier)
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())

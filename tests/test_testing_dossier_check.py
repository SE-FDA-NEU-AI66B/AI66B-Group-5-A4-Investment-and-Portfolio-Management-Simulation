"""Regression checks for scripts/check_testing_dossier.py (#121)."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_testing_dossier.py"
SPEC = importlib.util.spec_from_file_location("check_testing_dossier", SCRIPT)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def test_multi_node_row_reports_a_missing_second_node(tmp_path):
    dossier = tmp_path / "testing.md"
    dossier.write_text(
        "## 3. Automated tests\n"
        "| Case IDs | Test location | State |\n"
        "| --- | --- | --- |\n"
        "| TC-US01-01 | "
        "`tests/test_auth_m4.py::test_tc_us01_01_register_then_valid_session_opens_portfolio`; "
        "`tests/test_auth_m4.py::test_missing_second_node` | Branch |\n"
        "## 4. What the tests found\n",
        encoding="utf-8",
    )

    result = checker.check(dossier)

    assert result["checked"] == 2
    assert len(result["failures"]) == 1
    assert "test_missing_second_node" in result["failures"][0]


def test_shorthand_second_node_inherits_the_row_file(tmp_path):
    dossier = tmp_path / "testing.md"
    dossier.write_text(
        "## 3. Automated tests\n"
        "| Case IDs | Test location | State |\n"
        "| --- | --- | --- |\n"
        "| TC-US06-02 | "
        "`tests/test_portfolio_m4.py::test_tc_us06_02_one_holding_current_quote_exact_integer_values` "
        "and `::test_tc_us06_02_only_the_signed_in_accounts_holding_is_counted` | Branch |\n"
        "## 4. What the tests found\n",
        encoding="utf-8",
    )

    result = checker.check(dossier)

    assert result["checked"] == 2
    assert result["failures"] == []


def test_current_dossier_resolves_every_node():
    result = checker.check(ROOT / "docs" / "testing.md")

    assert result["failures"] == []
    assert result["checked"] >= 34
    assert result["pending"] == []

# Milestone 4 boundary and mutation audit

Independent audit for [#121](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/issues/121),
performed on 31 October 2026 by @nguyentue110. This document records what was
executed, not what the case table claims. It does not edit the shared case
table, which #118 owns.

## 1. Scope and method

- Baseline: `main` at `85902de`, the merge of #119.
- Sell evidence: branch `test/120-sell-boundaries` at `21c7a97` (PR #133). The
  sell cases were audited on that branch because PR #133 was still open.
- Every focused run used the repository virtual environment with an explicit
  `PYTHONPATH` pointing at the audited worktree, because that environment is
  editable-installed from another worktree.
- Mutation runs changed one rule, captured the red result, restored the rule,
  and reran the same node green. `git diff` was clean after each restore.
- Full suite on `main`: `285 passed, 2 skipped`.
- Focused `tests/test_auth_m4.py tests/test_buy_m4.py`: `18 passed`.

This is not the independent clean-clone result. #123 owns that check.

## 2. Boundary matrix

| Number or rule | Below / at / above | Executed evidence | Result |
|---|---|---|---|
| Password minimum 8 | 7 / 8 | `test_tc_us01_03_password_minimum_boundary[7-False]`, `[8-True]` | 7 returns 422 with no account; 8 returns 201 and one account |
| Password maximum 128 | 128 / 129 | `test_tc_us01_04_password_maximum_boundary[128-True]`, `[129-False]` | 128 returns 201; 129 returns 422 with no account |
| Five-attempt lock | 4 / 5 failures | `test_tc_us01_05_fifth_failure_locks_and_correct_password_stays_locked` | Four failures return 401; fifth returns 429 `LOGIN_LOCKED` with `Retry-After: 900`; correct password still 429; stored `failed_attempts=5` and `locked_until` set |
| Initial capital 100,000,000 | 99,999,999 / 100,000,000 / 100,000,001 | `test_tc_us02_03_client_supplied_balances_are_ignored`, `test_tc_us02_01_registration_grants_exactly_once` | Client values on both sides are ignored; persisted grant is exactly 100,000,000 |
| Duplicate registration keeps grant | duplicate request after 100,000,000 | `test_tc_us01_02_duplicate_wrong_password_and_csrf_refused_without_new_records` | Duplicate returns 409; stored balance remains 100,000,000 |
| Buy quantity | 0 / 1 | `test_tc_us04_02_zero_quantity_is_rejected_without_trade`, `test_tc_us04_01_preview_has_no_write_then_buy_records_exact_amount` | 0 returns `INVALID_QUANTITY` with no trade; 1 records exact cash and holding |
| Quote age | 900 / 901 seconds | `test_tc_us04_03_quote_age_boundary[900-True]`, `[901-False]` | 900 is allowed; 901 returns `QUOTE_STALE` with no write |
| Available cash | exact cost / cost - 1 VND | `test_tc_us10_01_cash_at_exact_cost_and_one_vnd_short` | Exact cost is allowed; 1 VND short is blocked, reports a 1 VND shortfall, and confirmation returns `INSUFFICIENT_CASH` with no write |
| Sell quantity | 0 / 1 / 1000 / 1001 with 1000 held | `test_tc_us05_03_quantity_boundaries` | 0 returns `INVALID_QUANTITY`; 1 and 1000 succeed; 1001 returns `INSUFFICIENT_SHARES` with no write |
| Sell cost basis and cash | partial 400 of 1000, then full 600 | `test_tc_us05_01_partial_then_full_sale_preserves_cash_and_cost_basis` | Allocated plus remaining cost stays 28,000,000; cash ends at 102,000,000; realised P&L totals 2,000,000 |
| Sell quote change and age | changed timestamp / 901 seconds old | `test_tc_us05_04_changed_and_stale_quote_are_refused_before_commit` | `QUOTE_CHANGED` and `QUOTE_STALE` both refuse before commit with no writes |
| Sell oversell route | 800 requested with 500 held | `test_tc_us05_05_sell_route_rejects_oversell_before_write` | Preview says not submittable; confirmation returns 409 `INSUFFICIENT_SHARES` with no writes |

## 3. Mutation evidence review

| Case | Rule changed | Red result | Restored result | Verdict |
|---|---|---|---|---|
| #117 TC-US04-03 | `-300 <= age <= 900` to `-300 <= age < 900` | `[900-True]` failed with `QUOTE_STALE`; `[901-False]` passed | 2 passed | Valid boundary proof; current code has `<= 900` |
| #119 TC-US01-03 | `PASSWORD_MIN_LENGTH` 8 to 7 | `[7-False]` failed with `assert 201 == 422` | 1 passed | Valid boundary proof; current code has 8 |
| #120 TC-US05-03 | `quantity > held` to `quantity >= held` | `[1000-True]` failed with `INSUFFICIENT_SHARES` | 1 passed | Valid boundary proof on PR #133; current branch has `>` |

The sell mutation was rerun on `21c7a97` during this audit. The buy and account
mutations were rerun on `85902de`. No mutation was left in any worktree.

## 4. Case ID resolution

`python scripts/check_testing_dossier.py` reads section 3 of `docs/testing.md`,
finds every backticked `tests/...py::function` mapping, and checks the file and
function exist. It also warns when a function name does not carry its TC ID.

Result on `main`:

```text
Checked 14 executable mappings: 14 resolved, 0 missing, 0 warnings, 3 rows still planned.
PENDING TC-US03-01 has no executable node (line 76)
PENDING TC-US05-01 has no executable node (line 77)
PENDING TC-US06-01 has no executable node (line 78)
```

The three pending rows are the grouped US03, US05 and US06 ranges. US05 gains
five executable mappings on PR #133. US03 (#124) and US06 (#122) still have no
tests on any merged branch, so they are follow-ups below, not completed evidence.

## 5. Findings and follow-ups

1. **Covered now:** all 14 executable mappings on `main` resolve, and the
   password, lockout, capital, buy, quote-age and available-cash boundaries have
   evidence on both sides of each cited number.
2. **Covered by PR #133:** US05 quantity, cost basis, cash conservation and
   quote change boundaries have red/green evidence on `21c7a97`. Merge #133
   before treating those cases as `main` evidence.
3. **Follow-up #124:** US03 query lengths 50 and 51 have no executable test on
   `main`. The `124-tests-us03` branch currently points at the same commit as
   `main`, so the dossier must keep US03 planned.
4. **Follow-up #122:** US06 portfolio states and valuation have no executable
   test on `main`. Keep US06 planned.
5. **Documentation state:** US01/US02 rows still say `Branch #119` after the
   merge, and US05 rows are still marked `Planned` on `main`. This is a stale
   label, not a missing test, and #118 should reconcile it in the final table.
6. **Optional strengthening:** `TC-US01-05` proves four failures return 401 and
   the fifth locks, but does not assert `locked_until IS NULL` before the fifth
   request. The 401 responses imply it; an explicit assertion would make the
   boundary self-documenting.
7. **Review requirement:** left a substantive review on @bianh13's buy-test PR
   [#128](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/pull/128#pullrequestreview-5721779437).
   It confirms the reproduced quote-age mutation and asks for an immediate
   post-preview state check in TC-US10-03, which currently samples state only
   after the preview.

## 6. Reproduce

```text
python scripts/check_testing_dossier.py
python -m pytest tests/test_auth_m4.py tests/test_buy_m4.py -q
python -m pytest -q
```

For the sell cases, run the same commands from the PR #133 worktree, where
`tests/test_sell_m4.py` exists.

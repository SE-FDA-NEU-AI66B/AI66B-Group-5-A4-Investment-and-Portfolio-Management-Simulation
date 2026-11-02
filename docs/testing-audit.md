# Milestone 4 boundary and mutation audit

Independent audit for [#121](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/issues/121),
updated 2 November 2026 by @nguyentue110. This document records what was
executed, not what the case table claims. It does not rewrite the shared case
table, which #118 owns.

## 1. Scope and method

- Baseline: `main` at `6381e55`, which includes #119, #124/#135, #122/#140,
  #120/#133 and #123/#142.
- Sell evidence: the US05 tests merged into `main` through #133 at `0ab00f2`.
  The mutation-tested head `e34207f` is the exact head that merged, and the HTTP
  oversell case seeds a current session and quote, so it does not depend on the
  date of the run.
- Every focused run used the repository virtual environment with an explicit
  `PYTHONPATH` pointing at the audited worktree, because that environment is
  editable-installed from another worktree.
- Mutation runs changed one rule, captured the red result, restored the rule,
  and reran the same nodes green. `git diff` was clean after each restore.
- Full suite on `main`: `320 passed, 2 skipped`.
- Full suite on this audit branch: `323 passed, 2 skipped`.
- Focused `tests/test_auth_m4.py tests/test_buy_m4.py`: `18 passed`.
- Focused `tests/test_portfolio_m4.py`: `19 passed`.

The independent clean-clone check is recorded in `docs/SETUP.md`: Bùi Khang
Long, 2 November 2026, `main` at `fc47196`, `312 passed, 2 skipped`. That run
predates #133 and #142, so its count is not the current count above.

## 2. Boundary matrix

| Number or rule | Below / at / above | Executed evidence | Result |
|---|---|---|---|
| Password minimum 8 | 7 / 8 | `test_tc_us01_03_password_minimum_boundary[7-False]`, `[8-True]` | 7 returns 422 with no account; 8 returns 201 and one account |
| Password maximum 128 | 128 / 129 | `test_tc_us01_04_password_maximum_boundary[128-True]`, `[129-False]` | 128 returns 201; 129 returns 422 with no account |
| Five-attempt lock | 4 / 5 failures | `test_tc_us01_05_fifth_failure_locks_and_correct_password_stays_locked` | Four failures return 401; fifth returns 429 `LOGIN_LOCKED` with `Retry-After: 900`; correct password still 429; stored `failed_attempts=5` and `locked_until` set |
| Initial capital 100,000,000 | 99,999,999 / 100,000,000 / 100,000,001 | `test_tc_us02_03_client_supplied_balances_are_ignored`, `test_tc_us02_01_registration_grants_exactly_once` | Client values on both sides are ignored; persisted grant is exactly 100,000,000 |
| Duplicate registration keeps grant | duplicate request after 100,000,000 | `test_tc_us01_02_duplicate_wrong_password_and_csrf_refused_without_new_records` | Duplicate returns 409; stored balance remains 100,000,000 |
| Market query limit 50 | 49 / 50 / 51 | `test_tc_us03_03_search_query_length_boundary[49]`, `[50]`, `[51]` | 49 and 50 preserved; 51 trimmed to 50 |
| Buy quantity | 0 / 1 | `test_tc_us04_02_zero_quantity_is_rejected_without_trade`, `test_tc_us04_01_preview_has_no_write_then_buy_records_exact_amount` | 0 returns `INVALID_QUANTITY` with no trade; 1 records exact cash and holding |
| Quote age | 900 / 901 seconds | `test_tc_us04_03_quote_age_boundary[900-True]`, `[901-False]` | 900 is allowed; 901 returns `QUOTE_STALE` with no write |
| Available cash | exact cost / cost - 1 VND | `test_tc_us10_01_cash_at_exact_cost_and_one_vnd_short` | Exact cost is allowed; 1 VND short is blocked, reports a 1 VND shortfall, and confirmation returns `INSUFFICIENT_CASH` with no write |
| Sell quantity | 0 / 1 / 1000 / 1001 with 1000 held | `test_tc_us05_03_quantity_boundaries` | 0 returns `INVALID_QUANTITY`; 1 and 1000 succeed; 1001 returns `INSUFFICIENT_SHARES` with no write |
| Sell cost basis and cash | partial 400 of 1000, then full 600 | `test_tc_us05_01_partial_then_full_sale_preserves_cash_and_cost_basis` | Allocated plus remaining cost stays 28,000,000; cash ends at 102,000,000; realised P&L totals 2,000,000 |
| Sell quote change and age | changed timestamp / 901 seconds old | `test_tc_us05_04_changed_and_stale_quote_are_refused_before_commit` | `QUOTE_CHANGED` and `QUOTE_STALE` both refuse before commit with no writes |
| Sell oversell route | 800 requested with 500 held | `test_tc_us05_05_sell_route_rejects_oversell_before_write` | Preview says not submittable; confirmation returns 409 `INSUFFICIENT_SHARES` with no writes |
| Portfolio empty state | zero holdings | `test_tc_us06_01_empty_holdings_total_equals_cash_with_browse_market` | Empty message; total equals cash; Browse the market link visible |
| Portfolio value and percent | 1 share / 1,000,000 shares; cost 0; one-VND gain and loss on 20,000 cost | `test_tc_us06_05_quantity_value_and_percent_boundaries` | Exact integer value, P&L and total; percent half-up gives +0.01 and -0.01, null when cost is 0 |
| Portfolio quote state | missing quote / two-hour-old quote / 900 / 901 / +300 / +301 seconds | `test_tc_us06_04_missing_quote_is_incomplete_and_never_valued_as_zero`, `test_tc_us06_04_delayed_quote_is_flagged_but_keeps_its_value`, `test_tc_us06_06_quote_age_boundary` | Missing quote is incomplete with null value and P&L, never 0; old quote is delayed but still valued; 900 and +300 current; 901 and +301 delayed |
| Portfolio privacy | guest / revoked session / disabled account / second account | `test_tc_us06_03_guest_gets_401_and_no_private_data`, `test_tc_us06_03_second_account_never_receives_the_first_accounts_data`, `test_tc_us06_03_revoked_session_or_disabled_account_gets_401` | 401 with no private data; a second account never sees the first account's holdings, including `?account_id=` tampering |

## 3. Mutation evidence review

| Case | Rule changed | Red result | Restored result | Verdict |
|---|---|---|---|---|
| #117 TC-US04-03 | `-300 <= age <= 900` to `-300 <= age < 900` | `[900-True]` failed with `QUOTE_STALE`; `[901-False]` passed | 2 passed | Valid boundary proof; current code has `<= 900` |
| #119 TC-US01-03 | `PASSWORD_MIN_LENGTH` 8 to 7 | `[7-False]` failed with `assert 201 == 422` | 1 passed | Valid boundary proof; current code has 8 |
| #124 TC-US03-03 | `MAX_QUERY_LENGTH` 50 to 49 | `[50]` and `[51]` failed | 3 passed | Valid lower-bound proof; restored to 50 |
| #124 TC-US03-03 | `MAX_QUERY_LENGTH` 50 to 51 | `[51]` failed; `[49]` and `[50]` passed | 3 passed | Valid upper-bound proof; restored to 50 |
| #120 TC-US05-03 | `quantity > held` to `quantity >= held` | `[1000-True]` failed with `INSUFFICIENT_SHARES` | 1 passed | Valid boundary proof; the code on `main` has `>` |
| #140 TC-US06-06 | `age > STALE_AFTER_SECONDS` to `>=` | `[900-False]` failed with `assert True is False` (900 s wrongly delayed) | 4 passed | Valid boundary proof; current code has `>` |

The sell mutation was rerun on `e34207f`, the head that merged as #133. The buy,
account, market and portfolio quote-age mutations were rerun on `6381e55`.
#140 also documented two US06-04 mutations (inner join, and counting an
unpriced holding as zero); this audit did not rerun those two, so they remain
author evidence, not independent evidence. No mutation was left in any worktree.

## 4. Case ID resolution

`python scripts/check_testing_dossier.py` reads section 3 of `docs/testing.md`,
finds every backticked `tests/...py::function` node, including multiple nodes
in one row, and checks the file and function exist. A backticked
`::function` shorthand inherits the last full path in the same row, so the
US06 rows merged in #140 are checked in full even though their later nodes are
abbreviated. The checker warns when the first function name does not carry its
TC ID.

Result on `main`:

```text
Checked 34 executable nodes: 34 resolved, 0 missing, 0 warnings, 0 rows still planned.
```

US05 is no longer pending: #133 merged its five mappings at `0ab00f2`, bringing
the table from 29 to 34 resolved nodes.

A small regression file, `tests/test_testing_dossier_check.py`, proves that a
row with one valid node and one missing node is reported as a failure instead
of silently passing, and that a `::function` shorthand resolves against its
row's file.

## 5. Findings and follow-ups

1. **Covered now:** all 34 executable nodes on `main` resolve, including both
   nodes in the US03 row, all three US06 privacy nodes and the five US05 nodes.
   Password, lockout, capital, market query, buy, quote-age, available-cash,
   sell quantity, cost basis, sell quote and portfolio value/percent/quote-age
   boundaries have evidence on both sides of each cited number.
2. **US05 is now covered on `main`:** #133 merged at `0ab00f2`, so the sell
   quantity, cost basis, cash conservation and quote change cases are main
   evidence. The HTTP oversell case uses a current session and quote and passed
   the 31 October re-review before merge.
3. **#124 is now covered:** US03 query lengths 49, 50 and 51 have executable
   tests on `main` through #135, and both mutation directions were reproduced.
   The earlier "no executable tests" note for US03 is resolved.
4. **#122 is now covered:** #140 merged `tests/test_portfolio_m4.py` into
   `main` at `fc47196`, with 19 tests for empty, private, missing-quote,
   value/percent and quote-age states. US06 is no longer a follow-up.
5. **Documentation state:** US05 rows now say `Branch #120 Tue`, and
   US01/US02/US03/US06 rows still carry `Branch #...` labels after merge. The
   duplicate US10 `Branch #117` rows flagged on #139 are also stale. These are
   labels, not missing tests. The US06 rows abbreviate later nodes as
   `::function`; the checker expands them, but #118/#139 can still make the
   final table use full paths.
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
python -m pytest tests/test_testing_dossier_check.py -q
python -m pytest tests/test_auth_m4.py tests/test_buy_m4.py -q
python -m pytest -q
```

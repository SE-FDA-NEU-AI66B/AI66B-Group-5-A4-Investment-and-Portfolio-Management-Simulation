# Milestone 4 testing dossier — working draft

This document is incomplete until every case below has an executable test on
`main`, the final clean-clone run is captured, and another member reviews it.
The status column distinguishes current branch evidence from planned work.

## 1. What we test, and why

| Layer | Test | Why |
|---|---|---|
| Services (`accounts`, `market`, `orders`, `portfolio`) | Rule and boundary tests with fake repositories or temporary SQLite | Login lockout, quote freshness, available cash, shares and valuation decide whether a user can trade safely. |
| Repositories and database | Temporary SQLite tests with actual schema/migrations | SQL updates must conserve virtual cash and holdings, roll back on failure, and isolate accounts. |
| Routes/controllers | Flask test-client tests without starting a server | Check request validation, authentication/CSRF and public status/error contracts. |
| Interface | Focused browser checks for empty/loading/success/error; pytest for stable server-rendered HTML and response behavior | Async focus, recovery links and readable states need a browser; API and page contracts must still have machine checks. |

The highest risk is an incorrect account or trading calculation: a false success
can create a virtual trade or misreport cash. We prioritize numeric boundaries,
failure with no writes, and authentication before presentation-only details.

## 2. Test cases for every P0 story

`Branch` means the test exists in Thanh's [draft PR #128](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/pull/128), not yet on `main`.
`Planned` means the case is assigned but is not counted as automated evidence.
Every planned ID must be added to a test name or comment by its issue owner.

| ID | Story | Input | Expected result | Kind | Status/owner |
|---|---|---|---|---|---|
| TC-US01-01 | US01 access | Valid new account, then correct sign-in | Account/session created; protected route opens | Normal | Branch #119 Tue |
| TC-US01-02 | US01 access | Duplicate email or incorrect password | Request refused; no extra account/session | Error | Branch #119 Tue |
| TC-US01-03 | US01 access | Password lengths 7 and 8 | 7 refused, 8 accepted | Boundary | Branch #119 Tue |
| TC-US01-04 | US01 access | Password lengths 128 and 129 | 128 accepted, 129 refused | Boundary | Branch #119 Tue |
| TC-US01-05 | US01 access | Four failed logins, then fifth | Fifth locks account with retry period | Boundary/error | Branch #119 Tue |
| TC-US02-01 | US02 grant | Register one account | Exactly 100,000,000 VND once | Normal | Branch #119 Tue |
| TC-US02-02 | US02 grant | Log out/in repeatedly | Balance never granted again | Error prevention | Branch #119 Tue |
| TC-US02-03 | US02 grant | Client sends 99,999,999 then 100,000,001 VND initial cash | Both ignored; persisted grant remains 100,000,000 | Boundary/error | Branch #119 Tue |
| TC-US03-01 | US03 market | Search lowercase ticker and company text | Matching stored symbols and source/timestamp | Normal | Planned #124 Vu |
| TC-US03-02 | US03 market | Unknown symbol or failed DB read | 404 detail / 503 read with recovery; entered query preserved | Error | Planned #124 Vu |
| TC-US03-03 | US03 market | Query lengths 50 and 51 | 50 preserved; 51st character safely trimmed | Boundary | Planned #124 Vu |
| TC-US04-01 | US04 buy | Preview and buy one HPG share | Preview writes nothing; confirmed trade/cash/holding exact | Normal | Branch #117 Thanh |
| TC-US04-02 | US04 buy | Quantity zero | `INVALID_QUANTITY`; no trade | Error/boundary | Branch #117 Thanh |
| TC-US04-03 | US04 buy | Quote ages 900 and 901 seconds | 900 allowed; 901 `QUOTE_STALE`, no write | Boundary | Branch #117 Thanh |
| TC-US05-01 | US05 sell | Sell part of held position | Proceeds, cash, remainder and cost basis exact | Normal | Planned #120 Tue |
| TC-US05-02 | US05 sell | Request more than held | `INSUFFICIENT_SHARES`; no writes | Error | Planned #120 Tue |
| TC-US05-03 | US05 sell | Quantity 0, 1, exactly held, held + 1 | 0 and overheld refused; 1/exact held accepted | Boundary | Planned #120 Tue |
| TC-US06-01 | US06 portfolio | New signed-in account with zero holdings | Empty state and total = cash | Normal/boundary | Planned #81/#122 Long |
| TC-US06-02 | US06 portfolio | One holding and a current quote | Only own holding, cash, valuation and P&L exact | Normal/boundary | Planned #81/#122 Long |
| TC-US06-03 | US06 portfolio | Guest or second account requests first account's data | 401/private holdings never leak | Error | Planned #81/#122 Long |
| TC-US10-01 | US10 cash warning | Cash equals one-share cost, then one VND below | Exact balance allows; shortfall blocks with warning | Boundary/error | Branch #117 Thanh |
| TC-US10-02 | US10 cash warning | Preview 2 shares with cash for 1, then reduce to 1 | Warning clears and confirmation becomes available; no preview writes | Normal recovery | Branch #117 Thanh |
| TC-US10-03 | US10 cash warning | Cash falls one VND below cost after preview | Confirmation refuses with no trade or balance change | Error/race | Branch #117 Thanh |

## 3. Automated tests

From the repository root after following [SETUP](SETUP.md), run `pytest` in the
activated virtual environment. For the final evidence, run
`python -m pytest -v` and capture **all test names** in the screenshot after
all team PRs have merged. A screenshot is pending; the current branch is not a
substitute for the final `main` run.

| Case IDs | Test location and exact pytest function | State |
|---|---|---|
| TC-US04-01 | `tests/test_buy_m4.py::test_tc_us04_01_preview_has_no_write_then_buy_records_exact_amount` | Branch |
| TC-US04-02 | `tests/test_buy_m4.py::test_tc_us04_02_zero_quantity_is_rejected_without_trade` | Branch |
| TC-US04-03 | `tests/test_buy_m4.py::test_tc_us04_03_quote_age_boundary` (900/901 parameters) | Branch |
| TC-US10-01 | `tests/test_buy_m4.py::test_tc_us10_01_cash_at_exact_cost_and_one_vnd_short` (exact/short parameters) | Branch |
| TC-US10-02 | `tests/test_buy_m4.py::test_tc_us10_02_reducing_quantity_clears_warning` | Branch |
| TC-US10-03 | `tests/test_buy_m4.py::test_tc_us10_03_cash_shortfall_recheck_does_not_write` | Branch |
| TC-US01-01 | `tests/test_auth_m4.py::test_tc_us01_01_register_then_valid_session_opens_portfolio` | Branch #119 |
| TC-US01-02 | `tests/test_auth_m4.py::test_tc_us01_02_duplicate_wrong_password_and_csrf_refused_without_new_records` | Branch #119 |
| TC-US01-03 | `tests/test_auth_m4.py::test_tc_us01_03_password_minimum_boundary` (7/8 parameters) | Branch #119 |
| TC-US01-04 | `tests/test_auth_m4.py::test_tc_us01_04_password_maximum_boundary` (128/129 parameters) | Branch #119 |
| TC-US01-05 | `tests/test_auth_m4.py::test_tc_us01_05_fifth_failure_locks_and_correct_password_stays_locked` | Branch #119 |
| TC-US02-01 | `tests/test_auth_m4.py::test_tc_us02_01_registration_grants_exactly_once` | Branch #119 |
| TC-US02-02 | `tests/test_auth_m4.py::test_tc_us02_02_login_logout_cycles_never_regrant` | Branch #119 |
| TC-US02-03 | `tests/test_auth_m4.py::test_tc_us02_03_client_supplied_balances_are_ignored` | Branch #119 |
| TC-US03-01–03 | #124 to add exact paths after reviewed merge | Planned |
| TC-US05-01–03 | #120 to add exact paths after reviewed merge | Planned |
| TC-US06-01–03 | #122 to add exact paths after #81/#103 merge | Planned |

The 27 October PR #128 worktree check selected its `src` explicitly because a
reused virtual environment was editable-installed from an older worktree:
**236 passed, 2 skipped**. This is not the independent clean-clone result.
Long's #123 must repeat from an independent clean clone. The final document
will record the plain `pytest` result from that clone.

## 4. What the tests found

**Deliberate mutation, 27 October — TC-US04-03.** Temporarily changed the
quote age rule in `src/virtutrade/orders/service.py` from `age <= 900` to
`age < 900`. The 900-second case failed with `QUOTE_STALE`; the 901-second
case remained green. Restored the original rule before commit and reran:

```text
Mutation run: python -m pytest tests/test_buy_m4.py -k quote_age_boundary -v
test_tc_us04_03_quote_age_boundary[900-True] FAILED
test_tc_us04_03_quote_age_boundary[901-False] PASSED
E   virtutrade.orders.errors.OrderError: Price may be delayed. Generate demo quotes, then preview again.
================== 1 failed, 1 passed, 6 deselected in 0.55s ==================

Restored run: python -m pytest tests/test_buy_m4.py -k quote_age_boundary -v
test_tc_us04_03_quote_age_boundary[900-True] PASSED
test_tc_us04_03_quote_age_boundary[901-False] PASSED
======================= 2 passed, 6 deselected in 0.34s =======================
```

This demonstrates that the boundary test fails when the inclusive time rule
breaks. The final red/green evidence and full-suite screenshot will be added
after independent review; the deliberate mutation is absent from this branch.

### Deliberate mutation, 28 October - TC-US01-03

Temporarily changed `PASSWORD_MIN_LENGTH` in
`src/virtutrade/accounts/service.py` from `8` to `7`. The seven-character
case then returned 201 instead of the required 422:

```text
$ python -m pytest "tests/test_auth_m4.py::test_tc_us01_03_password_minimum_boundary[7-False]" -q
FAILED tests/test_auth_m4.py::test_tc_us01_03_password_minimum_boundary[7-False]
E   assert 201 == 422
1 failed in 0.45s
```

Restored the rule to `8` and reran the same case:

```text
$ python -m pytest "tests/test_auth_m4.py::test_tc_us01_03_password_minimum_boundary[7-False]" -q
1 passed in 0.27s
```

The mutation is absent from the branch. The complete US01/US02 file passes as
part of the full suite after restoration.

# Milestone 4 testing dossier

Every P0 case below names an executable test that exists on `main`. Section 3
records the independent clean-clone run (#123) and the latest full run on
`main`, and says which commit each one used.

## 1. What we test, and why

| Layer | Test | Why |
| ----- | ---- | --- |
| Services (`accounts`, `market`, `orders`, `portfolio`) | Rule and boundary tests with fake repositories or temporary SQLite | Login lockout, quote freshness, available cash, shares and valuation decide whether a user can trade safely. |
| Repositories and database | Temporary SQLite tests with actual schema/migrations | SQL updates must conserve virtual cash and holdings, roll back on failure, and isolate accounts. |
| Routes/controllers | Flask test-client tests without starting a server | Check request validation, authentication/CSRF and public status/error contracts. |
| Interface | Focused browser checks for empty/loading/success/error; pytest for stable server-rendered HTML and response behavior | Async focus, recovery links and readable states need a browser; API and page contracts must still have machine checks. |

The highest risk is an incorrect account or trading calculation: a false success
can create a virtual trade or misreport cash. We prioritize numeric boundaries,
failure with no writes, and authentication before presentation-only details.

## 2. Test cases for every P0 story

`On main (#PR)` means the named test exists on `main` and was merged through
that reviewed PR. No P0 case is counted as automated evidence before its test
is on `main`; at this revision no case remains branch-only or planned.

| ID | Story | Input | Expected result | Kind | Status/owner |
|---|---|---|---|---|---|
| TC-US01-01 | US01 access | Valid new account, then correct sign-in | Account/session created; protected route opens | Normal | On main (#132) Tue |
| TC-US01-02 | US01 access | Duplicate email or incorrect password | Request refused; no extra account/session | Error | On main (#132) Tue |
| TC-US01-03 | US01 access | Password lengths 7 and 8 | 7 refused, 8 accepted | Boundary | On main (#132) Tue |
| TC-US01-04 | US01 access | Password lengths 128 and 129 | 128 accepted, 129 refused | Boundary | On main (#132) Tue |
| TC-US01-05 | US01 access | Four failed logins, then fifth | Fifth locks account with retry period | Boundary/error | On main (#132) Tue |
| TC-US02-01 | US02 grant | Register one account | Exactly 100,000,000 VND once | Normal | On main (#132) Tue |
| TC-US02-02 | US02 grant | Log out/in repeatedly | Balance never granted again | Error prevention | On main (#132) Tue |
| TC-US02-03 | US02 grant | Client sends 99,999,999 then 100,000,001 VND initial cash | Both ignored; persisted grant remains 100,000,000 | Boundary/error | On main (#132) Tue |
| TC-US03-01 | US03 market | Search mixed-case ticker and lowercase company text; view a stale stored quote | Matching stored symbol; source, quote time and stale state reflect the temporary DB; stale detail is marked delayed | Normal/integrity | On main (#135) Vu |
| TC-US03-02 | US03 market | Unknown symbol or failed DB read | Unknown HTML/JSON detail returns 404; storage failures return 503; entered query preserved on HTML search failure | Error | On main (#135) Vu |
| TC-US03-03 | US03 market | Query lengths 49, 50 and 51 | 49 and 50 preserved; 51st character safely trimmed | Boundary | On main (#135) Vu |
| TC-US03-04 | US03 market | Search for a query with no stored matches | 200 page preserves query and shows "No stocks match" empty state | Empty result | On main (#135) Vu |
| TC-US04-01 | US04 buy | Preview and buy one HPG share | Preview writes nothing; confirmed trade/cash/holding exact | Normal | On main (#128) Thanh |
| TC-US04-02 | US04 buy | Quantity zero | `INVALID_QUANTITY`; no trade | Error/boundary | On main (#128) Thanh |
| TC-US04-03 | US04 buy | Quote ages 900 and 901 seconds | 900 allowed; 901 `QUOTE_STALE`, no write | Boundary | On main (#128) Thanh |
| TC-US05-01 | US05 sell | Sell part of held position | Proceeds, cash, remainder and cost basis exact | Normal | On main (#133) Tue |
| TC-US05-02 | US05 sell | Request more than held | `INSUFFICIENT_SHARES`; no writes | Error | On main (#133) Tue |
| TC-US05-03 | US05 sell | Quantity 0, 1, exactly held, held + 1 | 0 and overheld refused; 1/exact held accepted | Boundary | On main (#133) Tue |
| TC-US05-04 | US05 sell | Quote timestamp changes, then quote is 901+ seconds old | `QUOTE_CHANGED` / `QUOTE_STALE`; no writes | Error/boundary | On main (#133) Tue |
| TC-US05-05 | US05 sell | HTTP preview then oversell confirmation | Route returns 409 `INSUFFICIENT_SHARES`; no writes | Error/route | On main (#133) Tue |
| TC-US06-01 | US06 portfolio | New signed-in account with zero holdings | Empty state, total = cash, visible Browse the market link | Normal/boundary | On main (#140) Long |
| TC-US06-02 | US06 portfolio | One holding and a current quote | Only own holding, cash, valuation and P&L exact integers | Normal | On main (#140) Long |
| TC-US06-03 | US06 portfolio | Guest, revoked session, disabled account or second account requests first account's data | 401 for guest/invalid session; second account sees only its own data; private holdings never leak | Error | On main (#140) Long |
| TC-US06-04 | US06 portfolio | Holding with no quote row; holding with a two-hour-old quote | No-quote holding shown as incomplete (value/P&L null, not 0, total flagged); old quote flagged delayed but still valued | Error | On main (#140) Long |
| TC-US06-05 | US06 portfolio | Quantity 1 and 1,000,000; cost 0; one-VND gain/loss on 20,000 cost | Exact integer value/P&L/total; percent half-up (+0.01 / -0.01), null when cost is 0 | Boundary | On main (#140) Long |
| TC-US06-06 | US06 portfolio | Quote age 900 and 901 seconds; 300 and 301 seconds in the future | 900 and +300 current; 901 and +301 delayed | Boundary | On main (#140) Long |
| TC-US10-01 | US10 cash warning | Cash equals one-share cost, then one VND below | Exact balance allows; shortfall blocks with warning | Boundary/error | On main (#128) Thanh |
| TC-US10-02 | US10 cash warning | Preview 2 shares with cash for 1, then reduce to 1 | Warning clears and confirmation becomes available; no preview writes | Normal recovery | On main (#128) Thanh |
| TC-US10-03 | US10 cash warning | Cash falls one VND below cost after preview | Confirmation refuses with no trade or balance change | Error/race | On main (#128) Thanh |

## 3. Automated tests

`requirements.txt` contains application/runtime dependencies and is deliberately
not the source for test tools. Install the test dependencies into the same
virtual environment used for the app. The server-rendered tests need `pytest`:

```text
python -m pip install pytest
python -m pytest -q tests/test_market_states.py
```

Browser regression scripts additionally need Playwright 1.63.0 and, for the
Edge-specific checks on Windows, Microsoft Edge installed:

```text
python -m pip install playwright==1.63.0
python scripts/check_market_keyboard_focus_ui.py --evidence-dir docs/images/ui/market-four-states
```

To install both test tools at once, use
`python -m pip install pytest playwright==1.63.0`. These packages are
development/QA-only and are intentionally not added to the runtime
`requirements.txt`.

For the full suite, follow [SETUP](SETUP.md) from a clean clone, put the new
venv on PATH and run plain `pytest -v` from the repository root:

```text
pytest -v
```

| Case IDs | Test location and exact pytest function | State |
|---|---|---|
| TC-US04-01 | `tests/test_buy_m4.py::test_tc_us04_01_preview_has_no_write_then_buy_records_exact_amount` | On main (#128) |
| TC-US04-02 | `tests/test_buy_m4.py::test_tc_us04_02_zero_quantity_is_rejected_without_trade` | On main (#128) |
| TC-US04-03 | `tests/test_buy_m4.py::test_tc_us04_03_quote_age_boundary` (900/901 parameters) | On main (#128) |
| TC-US10-01 | `tests/test_buy_m4.py::test_tc_us10_01_cash_at_exact_cost_and_one_vnd_short` (exact/short parameters) | On main (#128) |
| TC-US10-02 | `tests/test_buy_m4.py::test_tc_us10_02_reducing_quantity_clears_warning` | On main (#128) |
| TC-US10-03 | `tests/test_buy_m4.py::test_tc_us10_03_cash_shortfall_recheck_does_not_write` | On main (#128) |
| TC-US01-01 | `tests/test_auth_m4.py::test_tc_us01_01_register_then_valid_session_opens_portfolio` | On main (#132) |
| TC-US01-02 | `tests/test_auth_m4.py::test_tc_us01_02_duplicate_wrong_password_and_csrf_refused_without_new_records` | On main (#132) |
| TC-US01-03 | `tests/test_auth_m4.py::test_tc_us01_03_password_minimum_boundary` (7/8 parameters) | On main (#132) |
| TC-US01-04 | `tests/test_auth_m4.py::test_tc_us01_04_password_maximum_boundary` (128/129 parameters) | On main (#132) |
| TC-US01-05 | `tests/test_auth_m4.py::test_tc_us01_05_fifth_failure_locks_and_correct_password_stays_locked` | On main (#132) |
| TC-US02-01 | `tests/test_auth_m4.py::test_tc_us02_01_registration_grants_exactly_once` | On main (#132) |
| TC-US02-02 | `tests/test_auth_m4.py::test_tc_us02_02_login_logout_cycles_never_regrant` | On main (#132) |
| TC-US02-03 | `tests/test_auth_m4.py::test_tc_us02_03_client_supplied_balances_are_ignored` | On main (#132) |
| TC-US03-01 | `tests/test_market_search.py::test_tc_us03_01_search_is_case_insensitive_and_returns_stored_quote_metadata`; `tests/test_market_search.py::test_detail_html_and_stale_states` | On main (#135) |
| TC-US03-02 | `tests/test_market_search.py::test_tc_us03_02_unknown_ticker_and_storage_failures_return_errors` | On main (#135) |
| TC-US03-03 | `tests/test_market_search.py::test_tc_us03_03_search_query_length_boundary` (49/50/51 parameters) | On main (#135) |
| TC-US03-04 | `tests/test_market_search.py::test_tc_us03_04_search_with_no_matches_shows_empty_result` | On main (#135) |
| TC-US05-01 | `tests/test_sell_m4.py::test_tc_us05_01_partial_then_full_sale_preserves_cash_and_cost_basis` | On main (#133) |
| TC-US05-02 | `tests/test_sell_m4.py::test_tc_us05_02_oversell_is_refused_without_writes` | On main (#133) |
| TC-US05-03 | `tests/test_sell_m4.py::test_tc_us05_03_quantity_boundaries` (0/1/1000/1001 parameters) | On main (#133) |
| TC-US05-04 | `tests/test_sell_m4.py::test_tc_us05_04_changed_and_stale_quote_are_refused_before_commit` | On main (#133) |
| TC-US05-05 | `tests/test_sell_m4.py::test_tc_us05_05_sell_route_rejects_oversell_before_write` | On main (#133) |
| TC-US06-01 | `tests/test_portfolio_m4.py::test_tc_us06_01_empty_holdings_total_equals_cash_with_browse_market` | On main (#140) |
| TC-US06-02 | `tests/test_portfolio_m4.py::test_tc_us06_02_one_holding_current_quote_exact_integer_values` and `tests/test_portfolio_m4.py::test_tc_us06_02_only_the_signed_in_accounts_holding_is_counted` | On main (#140) |
| TC-US06-03 | `tests/test_portfolio_m4.py::test_tc_us06_03_guest_gets_401_and_no_private_data`, `tests/test_portfolio_m4.py::test_tc_us06_03_second_account_never_receives_the_first_accounts_data`, `tests/test_portfolio_m4.py::test_tc_us06_03_revoked_session_or_disabled_account_gets_401` (2 parameters) | On main (#140) |
| TC-US06-04 | `tests/test_portfolio_m4.py::test_tc_us06_04_missing_quote_is_incomplete_and_never_valued_as_zero` and `tests/test_portfolio_m4.py::test_tc_us06_04_delayed_quote_is_flagged_but_keeps_its_value` | On main (#140) |
| TC-US06-05 | `tests/test_portfolio_m4.py::test_tc_us06_05_quantity_value_and_percent_boundaries` (6 parameters) | On main (#140) |
| TC-US06-06 | `tests/test_portfolio_m4.py::test_tc_us06_06_quote_age_boundary` (900/901 and +300/+301 parameters) | On main (#140) |
| #125 Market read states | `tests/test_market_states.py` | On main (#136) |
| #125 Keyboard refresh focus | `scripts/check_market_keyboard_focus_ui.py` | On main (#136); requires Playwright and Edge |

### Full-suite results

| Run | Commit | Who / where | Result |
|---|---|---|---|
| Independent clean clone (#123, #142) | `fc47196` (`main` after #140) | Long, separate Windows 11 machine, fresh folder and venv, 2 November | **312 passed, 2 skipped** (314 collected) |
| Clean clone of current `main` | `6381e55` (`main` after #133 and #142) | @bianh13, fresh `git clone` into a new folder, new Python 3.13 venv with `pip install -e . pytest`, no `PYTHONPATH`, 2 November | **320 passed, 2 skipped** (322 collected) |

Long's run is the independent clean-clone evidence. Its unedited `pytest -v`
output, with every test name, is in six overlapping screenshots:
[1](images/m4/clean-clone-2026-11-02/pytest-v-1.png),
[2](images/m4/clean-clone-2026-11-02/pytest-v-2.png),
[3](images/m4/clean-clone-2026-11-02/pytest-v-3.png),
[4](images/m4/clean-clone-2026-11-02/pytest-v-4.png),
[5](images/m4/clean-clone-2026-11-02/pytest-v-5.png),
[6](images/m4/clean-clone-2026-11-02/pytest-v-6.png). The machine, Python
version, timings and the market page check are recorded under
[Independent verification](SETUP.md#independent-verification) in SETUP.

That run used `fc47196`, which was before #133 merged. It covers every P0 case
except the five US05 tests in `tests/test_sell_m4.py`. The current-`main` row
adds those tests. It ran on a fresh clone with a new venv and plain `pytest -v`,
but it is an author run, not a second independent check.

Earlier branch-local counts (236 passed on the #128 worktree on 27 October;
293 passed on `6eba4b0` on 1 November) are superseded by the two runs above.

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
breaks. The mutation is absent from `main`. @nguyentue110 independently
reproduced it in the #121 audit (PR #134).

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

### Deliberate mutation, 31 October - TC-US03-03

Temporarily changed the market query limit in both directions. Reducing the
limit to 49 made the 50- and 51-character cases fail, while the 49-character
case passed:

```text
$ python -m pytest tests/test_market_search.py -k "tc_us03_03 and (50 or 51)" -q
FAILED test_tc_us03_03_search_query_length_boundary[50]
FAILED test_tc_us03_03_search_query_length_boundary[51]
=========================== 2 failed, 9 deselected in 0.34s ===================
```

Increasing the limit to 51 made only the 51-character case fail:

```text
$ python -m pytest tests/test_market_search.py -k tc_us03_03 -v
FAILED test_tc_us03_03_search_query_length_boundary[51]
================== 1 failed, 2 passed, 8 deselected in 0.45s ==================
```

Restored the 50-character limit and reran all three boundary cases:

```text
$ python -m pytest tests/test_market_search.py -k tc_us03_03 -v
======================= 3 passed, 8 deselected in 0.40s =======================
```

The mutation is absent from the worktree.

After restoration, the local working-tree suite passed with
`python -m pytest`: **290 passed, 2 skipped**. This is branch-local evidence,
not the required clean-clone run from `main`.

### Deliberate mutations, 28 October - TC-US06-04 and TC-US06-06

Three temporary changes were made under `src/virtutrade/portfolio/`, each run
against the new test, then restored with `git checkout` (the mutations are
absent from the branch):

| Mutation | Test that turned red | Evidence |
|---|---|---|
| `service.py`: `age > STALE_AFTER_SECONDS` changed to `>=` | `test_tc_us06_06_quote_age_boundary[900-False]` | `assert True is False` (900 s wrongly delayed); 1 failed, 3 passed |
| `repository.py`: `LEFT JOIN price_quote` changed to `JOIN` | `test_tc_us06_04_missing_quote_is_incomplete_and_never_valued_as_zero` | `KeyError: 'XQB'` (holding without a quote vanished); 1 failed |
| `service.py`: unpriced holding counted as value 0 and `unpriced_count` forced to 0 | `test_tc_us06_04_missing_quote_is_incomplete_and_never_valued_as_zero` | `valuation_complete` stayed `True`; 1 failed |

After each restore the same selection passed (4 passed; 1 passed; 1 passed).
Fixtures use invented symbols (`XQA`, `XQB`) and explicit integers, so the
expected values are derived by hand and no server or real database is needed.

### Deliberate mutation, 30 October - TC-US05-03

Temporarily changed the oversell guard in `src/virtutrade/orders/sell.py` from
`quantity > held` to `quantity >= held`. Selling exactly the held quantity then
raised `INSUFFICIENT_SHARES` instead of removing the holding:

```text
$ python -m pytest "tests/test_sell_m4.py::test_tc_us05_03_quantity_boundaries[1000-True]" -q
FAILED tests/test_sell_m4.py::test_tc_us05_03_quantity_boundaries[1000-True]
E   virtutrade.orders.errors.OrderError: You hold 1,000 HPG; the maximum you can sell is 1,000.
1 failed
```

Restored the guard and reran the same case:

```text
$ python -m pytest "tests/test_sell_m4.py::test_tc_us05_03_quantity_boundaries[1000-True]" -q
1 passed
```

The mutation is absent from the branch. The complete US05 file passes as part
of the full suite after restoration.

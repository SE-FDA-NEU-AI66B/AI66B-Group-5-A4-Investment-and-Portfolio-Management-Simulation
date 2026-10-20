# P0 acceptance matrix (#82)

Owner @longbk761-bot · reviewer @VuSiSi · Sprint 3. This page covers the seven P0
stories (US01–US06, US10) and says which ones work end to end in the integrated
app, using a real database. A story counts as working only when **all** of its
acceptance criteria pass.

## How the audit runs

| Layer | Command | What it proves |
|---|---|---|
| Browser audit | `python scripts/check_p0_journeys.py --evidence-dir docs/images/ui/p0-audit` | 37 checks in a real browser (Edge by default), starting from the documented landing page `/`. It uses real registration, cookie sessions and CSRF. It captures screenshots and writes `p0-results.md` / `p0-results.json` with the commit, platform, browser and the observed text of every check. |
| CI regression | `python -m pytest tests/test_p0_acceptance.py -q` | The same journeys and server messages through Flask's test client. This runs in CI on every PR. Known gaps are `xfail(strict=True)` with their defect ID, so a fix forces this page to be updated. |

Both use a disposable SQLite database (`init_demo` in a temporary directory).
They make no DNSE calls, use no production keys and send no broker orders. The
browser audit labels its only database writes as fixtures:
- ageing one quote (stale flag),
- setting HPG to the AC reference prices (28,000 and 30,000),
- moving a quote after preview,
- emptying the quote table (empty state).

The browser audit needs the optional QA dependency `playwright==1.63.0` (see
SETUP). With Microsoft Edge installed, no browser download is needed. Use
`--browser chrome` or `--browser chromium` otherwise.

**Run record:** the commit, environment, timestamp and per-check results are in
the generated [p0-results.md](images/ui/p0-audit/p0-results.md). The script writes
that file, so nobody types the results by hand.

## Verdict per story

| Story | Verdict | Passing checks | Blocking gap |
|---|---|---|---|
| US01 Register / log in | **Partly works** | US01-1…6: landing, invalid email, short password, registration, duplicate email, lockout on the 5th wrong password (900 s) | D2: sign-in lands on `/market`, not the user's portfolio (US01-7) |
| US02 Initial capital | **Works** | US02-1 exactly 100,000,000 VND; US02-2 cash equals the grant plus trades after logout and login | none |
| US03 Market price | **Partly works** | US03-1 price, % change, UTC time and source for 12 tickers; US03-2 "Price may be delayed" after 15 min; S01 empty state; S02 error state | D1: no search or detail page, and no "Ticker not found" on Market (US03-3/4, #85) |
| US04 Market buy | **Partly works** | US04-1 guest guard and API 401; US04-2 reachable from Market; US04-3 1,000 HPG previews 28,000,000 with no trade written; US04-6 fill leaves 72,000,000 cash and 1,000 HPG; US04-7 BR1 message on bypass; US04-4 unknown ticker; S03 loading status | D4: 0 shares shows different wording from the AC (US04-5) |
| US05 Market sell | **Partly works** | US05-1 Sell from the holding row; US05-2 BR2 "You hold 500 HPG; the maximum you can sell is 500"; US05-3 1,000 HPG at 30,000 realises +2,000,000 and holding 0 | D3: a quote change after preview is rejected, not filled at the submitted price (US05-4) |
| US06 Portfolio | **Works** | US06-1 holding, average cost, total = cash + holdings; US05-1 unrealised +2,000,000; US06-2 "No positions yet" and account isolation; US06-3 load under 2 s; US06-4 guest 401 | none |
| US10 Balance warning | **Works** | US10-1 "Exceeds available balance by 12,000,000 VND", confirm disabled; US10-2 warning clears and confirm re-enables | none |

Cross-cutting checks:

| Check | Result |
|---|---|
| X01 | A logged-out token gets 401 and the trade form is disabled |
| X02 | No page-level horizontal scroll at 390 px on `/market`, `/trade`, `/portfolio`, `/login`, `/register` |
| X03 | Tab reaches every control on `/trade` in reading order, and the inputs have labels |
| X04 | No uncaught JavaScript errors |

**Summary:** 3 of 7 P0 stories fully work (US02, US06, US10). US01, US03, US04 and US05 are
partly working because of the four defects below.

## Defects found

| ID | Story | Owner | Steps to reproduce | Expected (AC) | Observed |
|---|---|---|---|---|---|
| D1 | US03 | @VuSiSi (#85) | Open `/market` and look for a ticker search or detail view | Search ticker X and open its detail page; an unknown ticker shows "Ticker not found" | There is no search box or detail page. "Ticker not found" appears only on `/trade` preview. Already tracked by #85, so no new issue was filed. |
| D2 | US01 | @nguyentue110 (#77) | Register, log out, then log in through the form | "I reach my own portfolio" | Redirects to `/market`. The JSON API already returns `redirect_to: /portfolio`. Now that #81 adds `/portfolio`, the form login can redirect there. |
| D3 | US05 | @bianh13 (PO) with @nguyentue110 (#79) | Preview a sell, let the quote move, then confirm | The order fills at the price quoted when it was submitted (BR3) | 409 "Price changed; refresh the preview before confirming." `docs/api-contract.md` documents this as QUOTE_CHANGED. Either the AC or the contract must change, so this needs a PO decision. |
| D4 | US04 | @bianh13 (#76) | On `/trade`, enter HPG and 0 shares | "Quantity must be a whole number of at least 1 share" | The page says "Enter a symbol and a whole number of at least 1 share." and the browser hint says "Value must be greater than or equal to 1." The server returns the AC wording (verified in CI), but the form never shows it. |

Observations that do not break an AC, recorded for the backlog:
- `/trade` has no account name or Log out in its header.
- Market has no direct Sell entry; Sell is reached from the Portfolio row.
- Quote times are shown as raw ISO UTC strings.
- The browser console shows expected 4xx responses for rejected previews.

## Limits of this evidence

- The browser audit is the author's own run on the author's machine, not
  independent clean-machine verification (#83) or the PDF page-3 screenshots
  (#88).
- The page captures exclude the browser chrome and address bar.
- "Loading" is observed by holding the preview request in the browser. Network
  failure during an order is covered by `scripts/check_buy_ui.py`.
# Market-to-Buy UI evidence - 20 October 2026

Issue #101, owner @bianh13, reviewer @nguyentue110. This presentation follow-up
is based on PR #100 (`27b0bf9`). It supports the existing US03/US04/US10 stories;
it does not introduce a new story or establish full M3 acceptance.

## Observed screens

Author QA: Windows, Python 3.10, headless Microsoft Edge and Playwright 1.63.0.
Desktop is 1440 x 1000; narrow-screen checks use 390 x 844. Registration,
sessions, CSRF and money transactions use the real application and isolated
SQLite databases. No test authentication callbacks are installed.

| Story / concern | Observation | Capture |
|-----------------|-------------|---------|
| US03 | Stored prices, names, source labels and UTC+7 quote times; per-row Buy survives polling | [Market](images/ui/market-buy-2026-10-20/market-desktop.png) |
| US04 | Buy HPG opens the form with HPG selected; search Hoa finds Hoa Phat; ArrowDown/Enter selects HPG | [Picker](images/ui/market-buy-2026-10-20/stock-picker-desktop.png) |
| US04 | 1,000 HPG at 28,000 costs 28,000,000; available cash 100,000,000; cash after purchase 72,000,000 | [Preview](images/ui/market-buy-2026-10-20/buy-preview-desktop.png) |
| US04 | Actual confirmation persists the purchase and displays cash/holding/order receipt | [Receipt](images/ui/market-buy-2026-10-20/buy-disconnect-receipt.png) |
| US10 | 4,000 HPG produces a 12,000,000 shortfall; confirmation is disabled and correcting quantity restores it | [Mobile warning](images/ui/market-buy-2026-10-20/buy-shortfall-mobile.png) |
| Quote protection | A deliberately aged temporary quote is rejected; visible Generate demo quotes recovers | [Stale quote](images/ui/market-buy-2026-10-20/buy-disconnect-stale-quote.png) |
| Ambiguous POST | Server commits before response disconnect/502; form locks without retry | [Unknown result](images/ui/market-buy-2026-10-20/buy-gateway-unknown-result.png) |
| Responsive layout | Buy form fits narrow viewport; Market table scrolls within its region | [Buy](images/ui/market-buy-2026-10-20/buy-preview-mobile.png), [Market](images/ui/market-buy-2026-10-20/market-mobile.png) |
| Picker states | Loading, no available stocks, failed GET with Retry, recovered list | [Loading](images/ui/market-buy-2026-10-20/picker-loading-mobile.png), [Empty](images/ui/market-buy-2026-10-20/picker-empty-mobile.png), [Error](images/ui/market-buy-2026-10-20/picker-error-mobile.png) |

Machine-readable reports in the same folder record observation timestamps and
fixture limitations. Error/empty/loading picker states deliberately intercept
only the quote GET response. The stale quote is a temporary-database fixture.
The actual buy tests assert two committed trades, cash 71,972,000 VND and 1,001
shares after the second response is lost. No provider is called by these tests.

## Reproduce

Follow SETUP and install `playwright==1.63.0` in the same virtual environment.
With Microsoft Edge installed on Windows, run:

```text
python scripts/check_market_buy_ui.py --evidence-dir docs/images/ui/local-review
python scripts/check_buy_ui.py
pytest -q
```

The optional evidence directory saves author page captures, without browser
chrome. These cannot replace #88's address-bar screenshots, #83's independent
machine check, or independent peer review. Portfolio remains pending #81 and
market search/detail remain pending #85. Keep the P0 statuses in ui.md honest.

## Integration boundary

The picker reads the existing API and the order summary uses server-returned
money. It does not set balances or authorize trades. Existing #98 sell side
metadata and receipt behavior are preserved for integration; the buy-only
controller still renders buy mode until the sell implementation is merged.
The DNSE worker remains in #60; simulation screenshots do not verify live prices.
No sector categories, fake charts or unsupported portfolio navigation are added.

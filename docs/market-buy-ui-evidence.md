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
metadata and receipt behavior are preserved. After synchronizing main at
`50ff313`, the controller renders both buy and sell; the Portfolio entry remains
pending #81.
The DNSE worker remains in #60; simulation screenshots do not verify live prices.
No sector categories, fake charts or unsupported portfolio navigation are added.

Local integration check `e783753` combines this UI with PR #60 `c044b9e`, #98
`561eb7c` and #99 `32119d3`. It passes **193 tests, 2 existing skips**. The
existing sell browser scenario also passes registration, buy, partial sale,
oversell rejection and full sale; its old single-sentence summary selector was
adapted to the structured Shares held row (still asserts 1,000). The grant
scenario passes registration/login with exactly one 100,000,000 VND grant.
Integration captures are kept separately from the teammates' original evidence.

The earlier integration identified two shared-file resolution requirements: retain the side-aware new trade template/handler, and carry #99's
Market balance into the shared header only on Market (not a stale balance on
Trade). These checks do not approve or merge the teammates' PRs, or establish a
visible Portfolio-to-Sell entry; the sell scenario explicitly visits its route.


## Requested dark price-board revision

The current captures use the PO-requested red/charcoal theme. The layout was
informed by the public [DNSE board](https://banggia.dnse.com.vn/): compact quote
columns and clear reference/movement information. VirtuTrade keeps its own
branding and only renders available fields. The watchboard and movement/count
panels use the same stored snapshot; they are not VNINDEX/VN30 data. Browser QA
also verifies that two quotes with missing references count as unclassified and
are excluded from movers. This explicit read-response fixture is not provider
verification. The two buy scenarios remain covered under the revised theme.

## Synchronization with merged sell and grant work

Before pushing the follow-up, main `50ff313` was merged locally. Three conflicts
were resolved in the Market template, Trade template and trade handler. The new
layout retains sell-side previews and receipts, the uncertain-order lock and
main's recovery wording. The one-time grant balance remains visible in the
Market header; it is not duplicated as stale cash on Trade. The sell browser
check now reads the structured Shares held row and still requires exactly 1,000.

The combined tree passes **161 tests, 2 existing skips**, Ruff, JavaScript
syntax and whitespace checks. Browser QA passes Market/picker/mobile states,
both real-auth buy scenarios, partial/full sale with oversell rejection, and
registration/login with exactly one grant. New sell/grant captures are stored
in the author's local QA folder to preserve the original teammate evidence.

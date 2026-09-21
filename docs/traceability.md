# Traceability

Every screen traces back to a feature and forward to the issue that built it.
This table is the single source of truth for Milestone 1 section 6 and for the
Milestone 4 report. Keep it current - a PR that adds a route and does not
update this file should not be approved.

| Route | Purpose | Access | Priority | Feature | Story issue | PR | Status |
|-------|---------|--------|----------|---------|-------------|-----|--------|
| `/` | Landing page; register or sign in to the simulation | G | P0 | F1 | #3, US01, US02 | #14 | Done |
| `/market` | Search a ticker and view its current reference price | U | P0 | F2 | US03 | | Not started |
| `/trade` | Place buy/sell orders and set stop-loss / take-profit conditions | U | P0 | F3 | #16, #17, US04, US05, US07, US10 | | Not started |
| `/portfolio` | Holdings with quantity, average cost, unrealised P&L and total value | U | P0 | F4 | #18, US06 | | Not started |
| `/history` | View completed and rejected transaction history | U | P1 | F5 | US08 | | Not started |
| `/performance` | View portfolio performance and compare with VN-Index | U | P2 | F6 | US09, US11 | | Not started |
| `/leaderboard` | View top players by performance and the current user's rank | U | P2 | F7 | US12 | | Not started |

**Access codes:** G = guest (not logged in) · U = authenticated user · A = admin

**Status:** Not started / In progress / Done

## Business rules

Numbered, so issues and tests can cite them.

| # | Rule | Enforced where | Tested by |
|---|------|----------------|-----------|
| BR1 | Order cost may not exceed the available cash balance | Order submission (`/trade`) | US04, US10 |
| BR2 | Sell quantity may not exceed the quantity held | Order submission (`/trade`) | US05 |
| BR3 | Market order fills at the price quoted when submitted | Order execution (`/trade`) | US04, US05 |
| BR4 | A stop-loss order triggers automatically and closes the entire position as soon as the market price reaches or falls below the threshold. A take-profit order triggers the same way once the price reaches or rises above its threshold. Default thresholds are 5% below and 10% above the average cost basis. | Threshold monitor, order execution (`/trade`) | US07 |
| BR5 | The initial virtual capital is fixed for every new account | Account initialization | US02 |
| BR6 | Average cost is the weighted average of every purchase | Buy execution (`/trade`) | US06 |
| BR7 | Portfolio and benchmark returns use the same start and end dates | Performance calculation (`/performance`) | US09, US11 |
| BR8 | The leaderboard includes active accounts and sorts by current percentage performance, with earliest achievement breaking ties | Ranking calculation (`/leaderboard`) | US12 |

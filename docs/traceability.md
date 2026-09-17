# Traceability

Every screen traces back to a feature and forward to the issue that built it.
This table is the single source of truth for Milestone 1 section 6 and for the
Milestone 4 report. Keep it current - a PR that adds a route and does not
update this file should not be approved.

| Route | Purpose | Access | Priority | Feature | Story issue | PR | Status |
|-------|---------|--------|----------|---------|-------------|-----|--------|
| `/` | Landing page | G | P0 | F1 | #3 | #14 | Done |
| `/trade` | Place a market buy or sell order | U | P0 | F2 | US04, US05 | | Not started |
| `/portfolio` | Holdings with quantity, average cost and unrealised P&L | U | P0 | F3 | US06 | | Not started |
| | | | | | | | |

**Access codes:** G = guest (not logged in) · U = authenticated user · A = admin

**Status:** Not started / In progress / Done

## Business rules

Numbered, so issues and tests can cite them.

| # | Rule | Enforced where | Tested by |
|---|------|----------------|-----------|
| BR1 | Order cost may not exceed the available cash balance | Order submission (`/trade`) | TBD (Sprint 2) |
| BR2 | Sell quantity may not exceed the quantity held | Order submission (`/trade`) | TBD (Sprint 2) |
| BR3 | Market order fills at the price quoted when submitted | Order execution (`/trade`) | TBD (Sprint 2) |
| BR4 | TBD - @Long | | |
| BR5 | TBD - @Vu | | |
| BR6 | Average cost is the weighted average of every purchase | Buy execution (`/trade`) | TBD (Sprint 2) |

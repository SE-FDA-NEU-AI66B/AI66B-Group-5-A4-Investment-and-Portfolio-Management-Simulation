# Traceability

Updated 4 October 2026 for #46/#48/#49/#50 and the #59 Sprint 3 carry-over. Sprint 1 closures record specification
history, not implementation. [API contract](api-contract.md) defines the routes
below, including examples/errors and access rules. Only routes explicitly marked
implemented run; designed endpoints remain future work.

| Story | Scenario steps | Acceptance checks | Screen / entry | Endpoint (proposed unless stated) | Tables | Work / history | Implementation / verification |
|-------|----------------|-------------------|----------------|----------------------------------|--------|----------------|-------------------------------|
| US01 P0 | S1.1 | Register, login, duplicate email, lockout | `/` | POST `/api/accounts`, POST `/api/sessions` | account | #46; history #13 | Specified; not implemented |
| US02 P0 | S1.1 | 100,000,000 VND once | `/` registration | POST `/api/accounts` | account | #46; history #14 | Schema default only; registration not implemented |
| US03 P0 | S1.2, S2.1, S6.3 | Price, daily change, timestamp, delayed/unknown ticker | `/market` | GET `/market` **implemented**; GET `/api/market/quotes/{symbol}` designed; list JSON implemented in resumed PR #60 (Sprint 3), review pending | instrument, price_quote | #50; history #15 | Snapshot subset implemented and locally tested; search/detail and live feed pending |
| US04 P0 | S1.3–S1.4 | Preview, valid fill, insufficient cash, invalid quantity | `/trade` | POST `/api/orders/preview`, POST `/api/orders/buy` | account, holding, trade, price_quote | #46/#49; history #16 | Specified; not implemented |
| US05 P0 | S2.2–S2.3 | Fill, realised result, oversell, quote time | `/trade` | POST `/api/orders/preview`, POST `/api/orders/sell` | account, holding, trade, price_quote | #46/#49; history #17 | Specified; not implemented |
| US06 P0 | S1.5, S2.1, S2.3 | Quantity, cost, P&L, NAV, empty portfolio | `/portfolio` | GET `/api/portfolio` | account, holding, instrument, price_quote | #46/#49; history #18 | Specified; not implemented |
| US10 P0 | S1.3 | Inline warning, disable/re-enable confirmation | `/trade` | POST `/api/orders/preview`, GET `/api/portfolio`; POST `/api/orders/buy` independently enforces BR1 | account, price_quote | #46/#49; history #22 | Specified; not implemented |
| US07 P1 | S3.1–S3.2 | Threshold trigger, no holding, single auto-close | `/trade` | Deferred | Future conditional-order storage; holding, trade | history #19 | Backlog; schema extension needed |
| US08 P1 | S2.4, S3.2 | Newest first, empty state, paging, auto-order label | `/history` | Deferred | trade; rejected-attempt/trigger metadata needs extension | history #20 | Backlog; current trade table stores fills only |
| US09 P2 | S4.1 | Time series, seven points, return, initial flat line | `/performance` | Deferred | Future daily valuation snapshots | history #21 | Backlog |
| US11 P2 | S4.2 | Matched dates, shorter history, percentage-point gap | `/performance` | Deferred | Future benchmark and valuation snapshots | history #23 | Backlog |
| US12 P2 | S4.3 | Top 10, own rank, timestamp tie-break | `/leaderboard` | Deferred | account; future performance-achievement timestamps | history #24 | Backlog |
| US13 P1 | S5.1–S5.3 | Admin-only, disabled-account denial, audit, no regrant | `/admin/accounts` | PATCH `/api/admin/accounts/{id}/status` (designed) | account, audit_event | #46/#48 | Specified; schema present, service not implemented |
| US14 P1 | S6.1–S6.3 | Valid/newer event only, deduplication, disconnect | DNSE adapter; external Machine User | Provider integration, not an app HTTP route | instrument, price_quote | #46/#48/#59 | Sprint 3 resumed; #59 Open; modular worker and list API tested; real authentication/subscription succeeded, but no tick/reference arrived in bounded probe; quote/unit comparison and review pending |

Access: market snapshot G/U (public read-only), trading/personal screens U,
administration A, quote ingestion M. Future authentication gates are server-side.

## Business rules and enforcement boundaries

| Rule | Enforcement design | Evidence today |
|------|--------------------|----------------|
| BR1 | Atomic buy transaction rechecks cash; nonnegative cash CHECK is a second guard | Schema only; no buy service |
| BR2 | Atomic sell transaction rechecks held quantity | Schema guards only; no sell service |
| BR3 | Capture accepted quote inside the order transaction | Snapshot schema only |
| BR4 | Conditional-order monitor with idempotent execution | Deferred |
| BR5 | Account creation grants 100,000,000 VND once; login/enable never grants again | Default only; service pending |
| BR6 | Exact total cost / quantity; partial-sale whole-VND allocation and final residual per money-rules.md | Integer cost storage; rounding contract ready for review, trading service pending |
| BR7 | Benchmark/performance service compares matching dates | Deferred |
| BR8 | Ranking uses achievement timestamps to break ties | Deferred |
| BR9 | Role check and atomic status-change/audit write | CHECKs/FKs only; service pending |
| BR10 | Adapter validates then updates only newer events | UNIQUE snapshot and positive-price/source CHECKs; adapter tested in resumed #60; live quote comparison pending |

`tests/test_market.py` verifies seed idempotence, persistence through app restart,
DB-backed rendering, seed/stale indicators, empty/error states and basic quote
constraints. Long owns independent verification and expanded regression coverage
in #51/#52; no peer work is recorded as completed on their behalf.

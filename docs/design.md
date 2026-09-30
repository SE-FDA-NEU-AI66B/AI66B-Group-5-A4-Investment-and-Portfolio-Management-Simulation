# Milestone 2 — VirtuTrade design

Team 05 · Topic A4 · Updated 30 September 2026.
PO / lead developer: @bianh13. Scrum Master: @nguyentue110.

**Working document, not final submission.** Sections 2, 4 and 6 have an
implementation-backed draft from #46/#48/#50. @VuSiSi completes architecture and
ADRs (#47); @bianh13 owns the API contract (#49). Independent setup
verification, final screenshots, peer review and merge remain pending.

## 1. Architecture

Owner: @VuSiSi, #47. Pending labelled container diagram and deployment detail.
Implementation: browser → HTTP GET → Flask (`app.py`) → SQL through `database.py`
→ local SQLite file → rendered HTML. DNSE Machine User/backend adapter are
design-only; Admin is a separate human role.

Current implementation uses Flask 3.1.3 and SQLite bundled with Python, within
the existing Python stack. Review references: [Flask installation](https://flask.palletsprojects.com/en/stable/installation/)
and [SQLite integration](https://flask.palletsprojects.com/en/stable/patterns/sqlite3/).
Vu records alternatives and change conditions in section 5 before finalization.

## 2. Data model

Baseline owner: @bianh13, #48. Independent ERD review/testing: @nguyentue110,
#56; Tuệ may redraw the model if it is unsuitable, keeping schema/dictionary in sync.
Source of truth: `database.py::SCHEMA`.

![ERD with keys and multiplicities](images/erd.png)

[Editable SVG](diagrams/erd.svg) · [Generator](../scripts/render_diagrams.py).
All six tables exist after init-db; only instrument and price_quote are seeded.
Empty account/holding/trade/audit tables do not implement those features. Deferred
extensions are documented in [traceability](traceability.md).

All columns are NOT NULL except `trade.realised_pnl_vnd`. An INTEGER PRIMARY KEY
is the SQLite row identifier. Timestamps are UTC ISO 8601 TEXT, validated by the
future service. Money is integer VND; services must validate integers because
SQLite type affinity alone is not an input validator.

| Table / purpose | Columns and types | Keys / constraints and rules |
|-----------------|-------------------|------------------------------|
| account: identity, role, state, virtual cash | id INTEGER; email TEXT COLLATE NOCASE; password_hash TEXT; role TEXT DEFAULT investor; status TEXT DEFAULT active; cash_vnd INTEGER DEFAULT 100000000; created_at TEXT | PK id; UNIQUE email (US01); role investor/admin and status active/disabled (BR9); cash >=0 (BR1 guard); default capital (BR5). Hashing, single grant and authorization need service code. |
| instrument: ticker identity | id INTEGER; symbol TEXT; name TEXT | PK id; UNIQUE symbol (US03/BR10). |
| price_quote: latest snapshot per ticker | id INTEGER; instrument_id INTEGER; price_vnd INTEGER; previous_close_vnd INTEGER; quoted_at TEXT; source TEXT | PK id; UNIQUE FK instrument_id → instrument.id; both prices >0; source seed/dnse (BR10). One snapshot, no tick history; newer-event ordering needs adapter logic. |
| holding: shares and remaining cost basis | id INTEGER; account_id INTEGER; instrument_id INTEGER; quantity INTEGER; cost_basis_vnd INTEGER | PK id; FKs account_id → account.id, instrument_id → instrument.id; UNIQUE(account_id, instrument_id); quantity >0, cost_basis_vnd >=0 (BR2/BR6 guards). Remove holding after full sale. |
| trade: executed fill | id INTEGER; account_id INTEGER; instrument_id INTEGER; side TEXT; quantity INTEGER; fill_price_vnd INTEGER; realised_pnl_vnd INTEGER NULL; executed_at TEXT | PK id; FKs account_id → account.id, instrument_id → instrument.id; side buy/sell; quantity/fill price >0 (BR2/BR3 guards). Realised P&L is set for sales; buys may use NULL. Rejected attempts/conditional metadata require later extension. |
| audit_event: account-status change | id INTEGER; admin_id INTEGER; target_account_id INTEGER; previous_status TEXT; new_status TEXT; occurred_at TEXT | PK id; both FKs → account.id; both statuses active/disabled (BR9). Future service checks admin role and writes status/audit atomically; FK alone cannot authorize. |

Multiplicities: instrument 1 → 0..1 price_quote; account 1 → 0..* holding;
instrument 1 → 0..* holding; account 1 → 0..* trade; instrument 1 → 0..* trade;
account 1 → 0..* audit_event twice (admin_id and target_account_id). Child FKs
are required. Every write connection must enable foreign keys, as init-db does.
No cascade delete is configured, preserving referenced parent rows.

Future buy/sell services must acquire a write transaction, re-read cash/quantity
and quote, validate BR1/BR2, and update cash, holding and trade atomically.
CHECK cannot enforce cross-table affordability or prevent overselling. Average
cost is cost basis / quantity using Decimal; display rounding must never feed
back into storage. Partial-sale allocation/rounding needs agreement and tests
before trading implementation; the skeleton performs no trades.

Seed contract: 12 instruments and 12 quote rows; four other tables empty.
Initialization adds missing demo rows without overwriting prices or duplicating
identities. Fixed seed timestamps/source remain unchanged. Future schema changes
require migrations; init-db is not a schema upgrade tool.

## 3. API design

Owner: @bianh13, #49. Pending >=6 endpoint contracts, >=2 meaningful error
codes and coverage for all P0 stories. Candidate mapping is in traceability.
Implemented: GET `/` redirects to `/market`; GET `/market` returns 200 HTML
(including empty state), or 503 HTML when the database is unavailable. The
server-rendered slice needs no separate JSON API. Other endpoints are unimplemented.

## 4. Walking skeleton

Owner: @bianh13, #50. **GET `/market`**, public/read-only, reads price_quote joined
with instrument: **12 rows** after clean initialization. Full commands: [SETUP](SETUP.md).
No credentials, external feed or separate DB server are needed.

The page lists ACB, BID, FPT, GAS, HPG, MBB, MSN, MWG, SSI, TCB, VCB and VNM,
with VND price, daily change, UTC time and Demo / seed badge. Quotes older than
15 minutes show a warning. Sample prices are illustrative, not live DNSE data.

Actual query in `database.py::read_market`:

```sql
SELECT i.symbol, i.name, q.price_vnd, q.previous_close_vnd,
       q.quoted_at, q.source
FROM price_quote AS q
JOIN instrument AS i ON i.id = q.instrument_id
ORDER BY i.symbol
```

The route only queries SQLite; init-db alone reads `data/demo-quotes.json`.
Committed `.env.example` documents configuration; real `.env` and database files
are ignored. Money remains integer VND; percentage display uses Decimal,
two decimal places and ROUND_HALF_UP.

Local tests verify repeatable seed, DB changes surviving a fresh app instance,
empty/unavailable states, seed/stale labels and constraints. Long owns independent
verification and expanded regression in #51/#52.

Final screenshot must show the running page and browser address bar (#53).
An automated page capture is supporting UI evidence, not a substitute for the
required browser-address-bar screenshot.

![Running market page, captured 30 September 2026](images/walking-skeleton-page.png)

This image is a Chrome headless capture of `http://127.0.0.1:5000/market` backed
by the initialized local SQLite database, not a mockup. Browser chrome is absent;
Vu supplies the final address-bar capture for the submission package.

## 5. Design decisions

Owner: @VuSiSi, #47. Pending two reviewed ADRs, each with alternatives, choice,
rationale and conditions for changing it. Assess Flask/SQLite against alternatives
and confirm or revise the implementation choices with the PO.

## 6. What changed since M1

Owner: @bianh13, #46. Recorded 30 September from instructor feedback and repo
inspection, not invented Sprint 2 Review outcomes.

| Change | Before | Revision / reason |
|--------|--------|-------------------|
| Align scenarios/stories | S1 promised social opinions; S2 indicators, quarterly data and what-if without matching stories | Narrow S1/S2 to supported trading/portfolio steps; preserve interview insights and explicitly defer unsupported needs; add later-priority scenarios. |
| Budget warning priority | US10 was P2 though S1 needed it before confirmation | US10 becomes P0; US04 independently enforces cash limits on the server. |
| Admin role | No management scenario/story | S5/US13/BR9 specify account enable/disable and audit with explicit 403/no-mutation checks; schema now, service later. |
| Machine User | Generic provider associated directly with price viewing | DNSE Websocket API is external Machine User in S6/US14/BR10; backend adapter validates and stores latest quotes; no human persona/login invented. |
| Honest implementation status | Landing route marked Done while app.py was empty | Trace every story with implementation status; only US03 snapshot subset is locally verified. Sprint 1 closures are specification history. |
| Review route | Authenticated-only market implied live feed | Public read-only demo snapshot lets instructor verify browser/backend/DB without credentials. Trading/private data still require future authentication. |

Deferred findings stay in the research record. Closed Sprint 1 issues are not
reopened or counted again. New issues remain open until DoD, review and merge;
remaining evidence requirements must also be met.

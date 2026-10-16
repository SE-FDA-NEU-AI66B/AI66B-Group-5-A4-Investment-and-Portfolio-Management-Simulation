# Buy and simulation implementation handoff — #76

Status: **partly works**. Buy rules, SQLite transactions, preview, form and local
simulation generation are implemented. Authentication #77 and portfolio #81
are not implemented here; there is no production login-to-buy acceptance yet.
Do not mark US04/US10 works or close #76 on the strength of a fake test session.

## Module boundaries

- `orders/routes.py`: HTTP/JSON validation, form and domain-error status mapping.
- `orders/service.py`: `preview_order` (buy/sell estimates), `execute_buy`, quantity,
  affordability, freshness and changed-quote rules. No Flask or SQL.
- `orders/repository.py`: one read snapshot or `BEGIN IMMEDIATE` transaction,
  re-read session/account/quote/holding, then cash/holding/trade SQL; no per-method commits.
- `orders/models.py`, `errors.py`: immutable inputs and domain failures.
- `simulation/service.py`: session/source/time checks. Its repository owns DB
  creation/refresh and uses the committed fixture without modifying that file.

The current concrete execution function is `execute_buy`; Tue's #79 should add
sell calculation/execution using the same unit of work and preview rather than
duplicate transaction or endpoint ownership. The #75 design remains subject to
Tue's agreement; any interface changes must be reflected there during integration.

## Auth adapter for Tue (#77)

The factory registers the order Blueprint, but **does not install test auth**.
Without a trusted identity resolver the API returns 503 SERVICE_UNAVAILABLE and
the form disables its controls. No guest trade or hard-coded account fallback exists.

The auth implementation should install these server-side extension callbacks:

```python
app.extensions['orders_identity'] = require_order_session
app.extensions['orders_csrf_token'] = current_order_csrf_token
```

`require_order_session(request)` must validate the server-side session cookie,
idle and absolute expiry, same-origin and the `X-CSRF-Token` on every POST, then
return the internal integer `auth_session.id`. It must never accept a browser's
account/session ID as proof. On failure, translate to OrderError AUTH_REQUIRED,
ACCOUNT_DISABLED or CSRF_FAILED, with safe messages. `current_order_csrf_token()`
supplies that authenticated session's CSRF token for the form; never expose a
session credential. The order service rechecks expiry/revocation/account status
using the same database transaction that commits the financial changes.

The auth_session storage columns follow #80's reviewed contract. Tests create
that minimal table and fake sessions solely in temporary databases. The browser
probe used an explicit test-only resolver; neither it nor fake credentials are
installed in the application. Long must retest with actual #77 registration/login.

## Implemented endpoints

| Route | Behavior |
|-------|----------|
| GET `/trade` | Buy form reachable by Market → Buy shares; no private values in the public shell |
| POST `/api/orders/preview` | Consistent read, no writes; warning/shortfall and can_submit update with quantity |
| POST `/api/orders/buy` | Integer-VND fill, 201 result only after atomic commit; stale/changed/shortage rejection |
| POST `/api/simulation/quotes/refresh` | Requires auth/CSRF adapter, simulation configuration and simulation-only DB |

The form prevents duplicate in-flight clicks, ignores obsolete preview responses
and disables confirmation on shortage. A network/unknown-response failure during
buy does not automatically retry and locks further submission pending manual
reconciliation. Durable idempotency is not claimed. Portfolio navigation and
post-login return handling must be completed with #77/#81/#85.

## Simulation setup

Use a **new path**, set `QUOTE_MODE=simulation` and
`DATABASE_PATH=instance/simulation.db`, then `python -m virtutrade init-demo`.
This exclusively creates a fresh DB with 12 explicitly simulated observations;
an existing file is refused, never reset. It creates no account or credential.
Auth #77 registration must grant initial capital, and the Generate demo quotes
button requires a real active session after integration. Without auth only the
market page can be browsed and the trading form remains unavailable.

The source constraint now permits `simulation`; atomic migration preserves old
IDs and records `simulation-source-v1` without consuming auth's user_version=2.
Manual generation advances simulation timestamps and invalidates old previews;
it never updates a mixed or DNSE database. The DNSE worker independently rejects
simulation DBs. `init-db` still never overwrites current prices.

## Verified and pending

115 automated tests pass; three existing auth/sell integration tests remain
skipped. New checks cover real SQLite success/rejection, exact amounts, rollback,
concurrent overspend, expired/revoked/disabled sessions, stale/future/changed
quotes, no-write preview, source guards and refusal to reset an existing DB.
An isolated real browser verified navigation, quantity correction, one persisted
buy, explicit demo refresh and unknown-result handling with test-only auth.
Ruff and JavaScript syntax checks pass. These do not replace independent-machine
SETUP, live auth integration, real portfolio navigation, peer review or merge.

To reproduce the optional browser smoke check on Windows with Edge installed,
install `playwright==1.63.0` in the development venv and run
`python scripts/check_buy_ui.py`. It starts a temporary local server/database
and a fresh headless browser, installs test-only auth on that server and cleans
up afterward. It does not change the production app or use real credentials.

# Application API contract

M2 baseline: #49, 3 October 2026. M3 shared contract: #75, 10 October 2026.
Owner: @bianh13. M3 reviewer: @nguyentue110; agreement pending review.

This is an implementation handoff, not a claim that all routes run. On `main`,
only GET `/` (302 to `/market`) and GET `/market` (200/503 HTML) are implemented.
The optional quote JSON endpoint and DNSE worker exist in draft PR #60, pending
integration, real-provider verification and review. All other endpoints below
are designed for later implementation; requesting them on current main yields 404.

## 1. Conventions and access

- JSON requests use `Content-Type: application/json`; malformed JSON returns
  400 `INVALID_JSON`, incorrect content type 415 `UNSUPPORTED_MEDIA_TYPE`.
  Unknown writable fields and invalid values return 422 `VALIDATION_ERROR`.
- Money is integer VND, quantity is an integer >=1 (booleans, fractional numbers
  and numeric strings are invalid). API monetary values and multiplication
  results must remain within 0..9,007,199,254,740,991; reject overflow with 422.
  Negative P&L is allowed within the corresponding signed range. Decimal display
  values are strings. No real money, broker orders, fees or taxes in this slice.
- Tickers are trimmed/uppercased, then resolved through `instrument.symbol`;
  unknown symbols return 404 `TICKER_NOT_FOUND`. UTC times are ISO 8601 with `Z`.
- G = Guest/public; U = active authenticated Investor; A = active Admin.
  Private routes derive account identity from the session, never request account_id.
  Re-check account status on every private request; role and status cannot be
  changed through registration/profile input. Admin management is P1.
- Planned auth uses an opaque server-side session cookie named `vt_session`,
  `HttpOnly`, `SameSite=Lax`, `Path=/`, and `Secure` on HTTPS. Local HTTP development
  alone may omit Secure. Rotate the session ID on login/registration and revoke on
  logout; use a 30-minute idle and 12-hour absolute expiry. Apply same-origin and
  CSRF checks to every state-changing browser request, including login/register.
  The future login page supplies a pre-auth CSRF token; missing/invalid
  `X-CSRF-Token` returns 403 `CSRF_FAILED`. No tokens or password hashes in JSON.
- Account/session endpoints require password hashing, session/CSRF storage and
  failed-login counters not present in the six-table M2 schema. Migrate these
  before implementation; do not store passwords or provider keys in account rows.
- JSON errors use `{"error":{"code":"...","message":"...","details":{}}}`.
  Private responses use `Cache-Control: no-store`; DB failures return 503
  `SERVICE_UNAVAILABLE`. Logs must omit credentials and session/CSRF values.
  The existing HTML market route retains its HTML 503 response.

## 2. Endpoint inventory

All errors below also use the shared validation/authorization rules above.

| Method | Path | Access / story | Input | Success output | Error codes | Status |
|--------|------|----------------|-------|----------------|-------------|--------|
| POST | `/api/accounts` | G; US01/US02 | email, password | 201 account id/email, cash_vnd=100000000; session cookie; Location `/api/portfolio` | 409 EMAIL_IN_USE; 422 VALIDATION_ERROR | Designed |
| POST | `/api/sessions` | G; US01 | email, password | 200 account id/role; session cookie | 401 INVALID_CREDENTIALS; 429 LOGIN_LOCKED; 403 ACCOUNT_DISABLED | Designed |
| DELETE | `/api/sessions/current` | U/A; US01 support | CSRF header; no body | 204; cookie expired, server session revoked | 401 AUTH_REQUIRED; 403 CSRF_FAILED | Designed |
| GET | `/market` | G/U; US03 | none | 200 HTML with quotes, including empty state | 503 HTML unavailable page | Implemented on main |
| GET | `/api/market/quotes` | G/U; US03 | no parameters | 200 quotes array; price/reference/time/source/stale/change | 503 MARKET_UNAVAILABLE | Implemented only in draft #60 |
| GET | `/api/market/quotes/{symbol}` | G/U; US03 | ticker path parameter | 200 one quote object; stale prices remain viewable | 404 TICKER_NOT_FOUND; 503 QUOTE_UNAVAILABLE | Designed |
| POST | `/api/orders/preview` | U; US04/US05/US10 | side=buy/sell, symbol, quantity | 200 estimate_vnd, available quantity/cash, shortfall, can_submit, warning and quote time/source; no writes | 422 INVALID_QUANTITY/VALIDATION_ERROR; 404 TICKER_NOT_FOUND; 409 QUOTE_STALE; 503 QUOTE_UNAVAILABLE | Designed |
| POST | `/api/orders/buy` | U; US04/US10 | symbol, quantity, expected_quote_at | 201 trade, cash and updated holding | 409 INSUFFICIENT_CASH/QUOTE_CHANGED/QUOTE_STALE; 422 INVALID_QUANTITY; 404 TICKER_NOT_FOUND; 503 QUOTE_UNAVAILABLE | Designed |
| POST | `/api/orders/sell` | U; US05 | symbol, quantity, expected_quote_at | 201 trade with realised_pnl_vnd, cash and remaining holding or null | 409 INSUFFICIENT_SHARES/QUOTE_CHANGED/QUOTE_STALE; 422 INVALID_QUANTITY; 404 TICKER_NOT_FOUND; 503 QUOTE_UNAVAILABLE | Designed |
| GET | `/api/portfolio` | U; US06/US10 | none; session owner only | 200 cash_vnd, holdings, total_value_vnd and valuation status | 401 AUTH_REQUIRED; 403 ACCOUNT_DISABLED | Designed |
| PATCH | `/api/admin/accounts/{id}/status` | A; US13 P1 | status=active/disabled | 200 id/status; audit entry for an actual transition | 403 ADMIN_REQUIRED; 404 ACCOUNT_NOT_FOUND; 409 SELF_DISABLE; 422 VALIDATION_ERROR | Designed, optional beyond P0 |

Shared private-route errors: 401 `AUTH_REQUIRED` for absent/expired session;
403 `ACCOUNT_DISABLED` for disabled accounts; 403 `ADMIN_REQUIRED` for an
Investor accessing admin routes; 403 `CSRF_FAILED` on state-changing requests.
No error partially updates cash, holdings, trades or audit events.

## 3. Registration and login examples

POST `/api/accounts` (CSRF token omitted from all examples):

```json
{"email":"learner@example.test","password":"example-only-passphrase"}
```

201 response (also sets the session cookie):

```json
{"account":{"id":1,"email":"learner@example.test","role":"investor","cash_vnd":100000000},"redirect_to":"/portfolio"}
```

Email is trimmed and case-insensitive; validate its syntax and a password of
8..128 characters without trimming the password. Reject client-supplied cash,
role/status and IDs. Atomically create exactly one account with its initial
capital; a unique-email collision returns 409:

```json
{"error":{"code":"EMAIL_IN_USE","message":"Email already in use","details":{}}}
```

POST `/api/sessions` accepts the same email/password fields and returns 200:

```json
{"account":{"id":1,"role":"investor"},"redirect_to":"/portfolio"}
```

Wrong/unknown credentials return the same 401 `INVALID_CREDENTIALS` message
`Invalid email or password`. For an existing account, the fifth consecutive
wrong password sets a 15-minute lock and returns 429 `LOGIN_LOCKED` with
`Retry-After: 900`; subsequent requests during the lock return remaining seconds.
Successful login after lock expiry clears the counter. Implement per-account
counters and IP throttling with expiry; current schema does not provide them.
Login, logout, repeat registration attempts and re-enabling an account never
grant capital again (BR5).

## 4. Quote and preview examples

GET `/api/market/quotes/HPG` returns a designed `quote` wrapper:

```json
{"quote":{"symbol":"HPG","name":"Hoa Phat Group","price_vnd":28000,"previous_close_vnd":27500,"reference_at":null,"quoted_at":"2026-10-03T02:00:00Z","source":"seed","stale":false,"change":"1.82"}}
```

This is an illustrative contract fixture, not a live market reading. The draft
list endpoint uses `{"quotes":[...]}` with the same quote fields. An empty list
is 200. A known instrument without a quote returns 503 `QUOTE_UNAVAILABLE` on
detail/preview/trade routes; an unknown ticker returns:

```json
{"error":{"code":"TICKER_NOT_FOUND","message":"Ticker not found","details":{"symbol":"UNKNOWN"}}}
```

Quotes older than 900 seconds remain visible with `stale:true`. Invalid/missing
timestamps are stale; timestamps more than 300 seconds ahead are invalid.
No valid same-day DNSE reference means `previous_close_vnd:null` and `change:null`,
not a seed fallback. The UI shows `Price may be delayed` or `Reference unavailable`.

POST `/api/orders/preview`:

```json
{"side":"buy","symbol":"HPG","quantity":1000}
```

At a fresh 28,000 VND quote and 100,000,000 VND cash, 200:

```json
{"side":"buy","symbol":"HPG","quantity":1000,"estimate_vnd":28000000,"cash_vnd":100000000,"available_quantity":0,"shortfall_vnd":0,"can_submit":true,"warning":null,"quote":{"price_vnd":28000,"quoted_at":"2026-10-03T02:00:00Z","source":"seed"}}
```

Preview never writes trades or reserves cash/shares. For US10, cash 500,000 VND
and estimated cost 800,000 VND return 200, `shortfall_vnd:300000`,
`can_submit:false`, `warning:"Exceeds available balance by 300,000 VND"`.
The form disables confirmation, recomputes the warning as quantity changes and
re-enables it at a cost <=500,000. Validate again on the backend at submission;
the preview is not authorization. Oversell preview similarly returns a warning
and `can_submit:false`, without a write.

## 5. Buy/sell execution and error examples

POST `/api/orders/buy`:

```json
{"symbol":"HPG","quantity":1000,"expected_quote_at":"2026-10-03T02:00:00Z"}
```

201 after a fresh 28,000 VND fill and initial cash 100,000,000:

```json
{"trade":{"id":1,"symbol":"HPG","side":"buy","quantity":1000,"fill_price_vnd":28000,"executed_at":"2026-10-03T02:00:03Z","realised_pnl_vnd":null},"cash_vnd":72000000,"holding":{"symbol":"HPG","quantity":1000,"cost_basis_vnd":28000000}}
```

For US04's 3,000 FPT at 120,000 VND and cash 72,000,000, return 409:

```json
{"error":{"code":"INSUFFICIENT_CASH","message":"Insufficient cash: this order needs 360,000,000 VND but only 72,000,000 VND is available","details":{"required_vnd":360000000,"available_vnd":72000000}}}
```

For quantity 0, fractional/string/bool quantities, return 422:

```json
{"error":{"code":"INVALID_QUANTITY","message":"Quantity must be a whole number of at least 1 share","details":{"field":"quantity"}}}
```

POST `/api/orders/sell` uses the same request shape. Selling all 1,000 HPG bought
for 28,000,000 VND at a fresh 30,000 VND quote (cash before=72,000,000) returns:

```json
{"trade":{"id":2,"symbol":"HPG","side":"sell","quantity":1000,"fill_price_vnd":30000,"executed_at":"2026-10-03T02:10:03Z","realised_pnl_vnd":2000000},"cash_vnd":102000000,"holding":null}
```

Trying to sell 800 when only 500 are held returns 409:

```json
{"error":{"code":"INSUFFICIENT_SHARES","message":"You hold 500 HPG; the maximum you can sell is 500","details":{"available_quantity":500,"requested_quantity":800}}}
```

Execution contract (BR1/BR2/BR3/BR6): begin a write transaction, re-read session
account status, cash/holding and latest quote; validate quantity, symbol,
freshness and the exact `expected_quote_at` from preview. A changed snapshot
returns 409 `QUOTE_CHANGED` (`Price changed; refresh the preview`); a stale quote
returns 409 `QUOTE_STALE` (`Price may be delayed; refresh before trading`).
Do not silently fill from a different timestamp or from an invalid future time.
Re-check affordability/availability using the accepted snapshot, then update
cash, the unique holding pair and trade together; roll back on any error.
A tick arriving after this transaction does not change the recorded fill.

Cost allocation follows [the exact rounding decision](money-rules.md). Delete
the holding on a full sale. Seed quotes can support a deliberately refreshed
simulation fixture, but the fixed September seed is stale and cannot authorize
a future trade; never rewrite seed timestamps merely to bypass the check.

No automatic retry of POST buy/sell after an uncertain network result: the
current schema has no durable idempotency key. The UI must show an unknown result
and refresh holdings; durable request deduplication requires a later migration.
These transaction behaviors remain planned, not implemented in M2.

## 6. Portfolio and administration examples

GET `/api/portfolio`, fresh US06 fixture:

```json
{"cash_vnd":40000000,"holdings":[{"symbol":"HPG","quantity":200,"cost_basis_vnd":6000000,"average_cost_vnd":"30000.00","price_vnd":33000,"market_value_vnd":6600000,"unrealised_pnl_vnd":600000,"unrealised_return_pct":"10.00","quoted_at":"2026-10-03T02:00:00Z","stale":false}],"total_value_vnd":46600000,"valuation_status":"current"}
```

Read holdings/cash/quotes in one DB read snapshot, deriving account ownership
from the session. An empty account returns `holdings:[]`, total=cash and
`message:"No positions yet"`. A stale available quote still values that holding,
with valuation status `delayed`. A missing/invalid price makes that row's value
and P&L NULL and the total NULL, status `incomplete`; never substitute zero.
Average cost and return are rounded display strings only; the stored cost basis
drives P&L. Target response time is <=2 seconds for the M2-sized fixture (US06),
to be measured once implemented.

PATCH `/api/admin/accounts/7/status`, body `{"status":"disabled"}`, returns
`{"account":{"id":7,"status":"disabled"}}` with 200 after an Admin check.
An actual transition updates account.status and inserts audit_event in one
transaction. Repeating the same status returns 200 without a duplicate audit;
block disabling the current admin with 409 `SELF_DISABLE`. Investor callers
get 403 with no mutation. A disabled account's existing sessions cannot authorize
private requests; enabling it does not reset cash, holdings or grant capital.

## 7. External DNSE boundary and verification

DNSE is an external Machine User, not `/api/dnse` or a login account. Only the
backend adapter holds its key/secret; the browser reads our database snapshots.
The optional draft connects to `wss://ws-openapi.dnse.com.vn/v1/stream?encoding=json`,
signs `api_key:timestamp:nonce` with HMAC-SHA256, then subscribes to G1 stock tick
and reference streams. Preserve provider time/source, reject invalid/equal/older
events and reconnect with fresh auth/subscriptions. Server-driven disconnection
and ping/pong are part of the provider protocol. See [DNSE guide](https://developers.dnse.com.vn/docs/guide/market-data/connect/)
and [official SDK](https://github.com/dnse-tech/openapi-sdk/tree/main/python/dnse/websocket).

PR #60 contains implementation and local tests for this optional path; real-provider acceptance
is waiting for keys under #59. No keys, real trades or broker tokens are required
to demonstrate the required seed-backed M2 slice.

Review method: match every P0 row in [traceability](traceability.md), check the
worked amounts against requirements and money rules, and run existing route/DB
tests for implemented behavior. Designed endpoints need service tests when built;
no screenshot or mock response here is evidence that they exist.

Auth design reference: [OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).


## 7. M3 shared order and simulation contract — #75

**Design handoff, not implemented behavior.** This section adds an explicit
simulation workflow to the M2 contract; existing production-like quote checks
still apply. Tue must review the shared interfaces before #75 is accepted.

### 7.1 File ownership and module interfaces

All paths below are relative to `src/virtutrade/` and describe planned files.

| Owner / issue | Primary files and responsibility | Interface supplied to other modules |
|---------------|----------------------------------|-------------------------------------|
| Thanh #76 | `orders/routes.py`, `orders/service.py`, `orders/repository.py`, `orders/models.py`, `orders/errors.py`; shared `orders/templates/orders/trade.html` and form script | Shared preview/execute entry points and buy calculation; routes own HTTP/error mapping, repository owns SQL/transaction |
| Tue #79 | `orders/sell.py` plus sell tests; coordinate additions to shared form/routes with Thanh | Pure sell calculation returning proceeds, remaining holding and realised P&L; no independent transaction or duplicate preview endpoint |
| Tue #77/#80 | `accounts/` plus versioned auth migrations | Resolve/revalidate session and account status, provide CSRF validation; private routes receive trusted account identity rather than client account_id |
| Long #81 | `portfolio/` | Read-only cash/holding/valuation snapshot for the authenticated account; trades do not call portfolio over HTTP |
| Vu #85 | `market/routes.py`, `market/service.py`, `market/repository.py`, templates/static | Own list/detail quote JSON and visible stock navigation; share one quote contract with #59 |
| Thanh #59 | Separate DNSE worker/provider adapter and its migrations | Persist validated provider events; reuse the market endpoints rather than register competing URL handlers |
| Thanh #76; reviewed with Tue | `simulation/` and CLI `init-demo` wiring | Explicit local-demo initialization and refresh described below; this implementation is part of #76, not completed by this design PR |

Agree changes to shared files before editing; only one Blueprint registers each
endpoint. Auth and trading migrations must be versioned/sequenced together;
quote schema changes must preserve old rows/IDs on upgrades. Module services use
plain values/domain errors; only controllers know HTTP, and only repositories
know SQLite. No internal HTTP calls connect these modules.

Proposed Python-facing contracts (names are agreed integration boundaries):

```text
preview_order(account_id, side, symbol, quantity, reader, now) -> OrderPreview
execute_order(session_id, side, symbol, quantity, expected_quote_at,
              unit_of_work, now) -> TradeResult
calculate_sell(holding, quantity, fill_price_vnd) -> SellResult
```

`OrderPreview` serializes to the fields in section 4. `TradeResult` uses section
5's `trade`, `cash_vnd` and `holding`. `SellResult` contains proceeds, allocated
cost, remaining quantity/cost and realised P&L, using money-rules.md. These are
domain values, not Flask responses. The execution service resolves the trusted
session/account again inside the transaction; it never accepts a browser's
account_id, cash or claimed preview authorization. An authenticated route passes
the server-side session identity, never a cookie secret into logs or JSON.

### 7.2 One atomic execution boundary

1. Controller validates JSON shape, same-origin/CSRF and obtains session identity.
2. Repository unit of work opens a connection with foreign keys enabled and
   acquires `BEGIN IMMEDIATE`; the service revalidates session expiry/revocation,
   account status, balance, holding and current quote using that connection.
3. Validate integer quantity, bounded money arithmetic, freshness and the exact
   preview timestamp. Reject shortage/stale/change before any financial write.
4. Calculate buy or sell using integer VND and the exact partial-sale allocation
   in money-rules.md. Update cash, upsert/delete the holding and insert one trade
   inside this same transaction. Repository methods never commit individually.
5. Commit once on success; any domain/storage exception rolls back everything.
   Return the saved fill result, then let the browser refresh its portfolio.

Preview uses one consistent read snapshot and never reserves cash/shares or
inserts a trade. Serialize concurrent writers; a second order must re-read the
post-first-order balance/holding. Use a bounded busy timeout; an unavailable
database returns 503 `SERVICE_UNAVAILABLE` with a useful message. If the client
cannot determine whether an order committed, show an unknown-result state and
refresh the portfolio; never automatically retry the order POST. Durable order
idempotency is not added or claimed by this contract.

### 7.3 Explicit local simulation quotes

The fixed M2 seed is historical and becomes stale. Loading a page, starting the
server or running `init-db` must not retimestamp it to make a trade succeed.
Instead, add a separately configured **simulation database** and explicit actions:

- Proposed settings: `QUOTE_MODE=simulation` and
  `DATABASE_PATH=instance/simulation.db`. Existing mode remains `seed` by default;
  DNSE mode and simulation mode are mutually exclusive for one configured DB.
- Proposed `python -m virtutrade init-demo` creates a **new** simulation database,
  using fixture instruments/prices with fresh generated simulation timestamps.
  It records `source=simulation`, not `seed` or `dnse`. It never copies real
  credentials or modifies the existing M2/DNSE DB. If the destination already
  exists, refuse with instructions to use refresh; never reset balances/holdings.
- Add `simulation` to the price_quote source constraint through a versioned
  migration preserving existing IDs/rows; update schema, dictionary and ERD in
  the implementation PR. Do not run a DNSE worker against a simulation DB, or a
  simulation writer against any database containing seed/DNSE quotes. Check both
  mode and stored sources before a refresh; reject a mixed DB without writes.
- On a local demo instance, an authenticated investor clicks **Generate demo
  quotes** in the market/trade UI. POST `/api/simulation/quotes/refresh` accepts an
  empty JSON object and requires same-origin/CSRF and an active account. It is
  unavailable outside simulation mode. Bind the classroom demo to localhost;
  document that all users of this demo DB share its simulated market.
- In one transaction, generate a new batch from the committed deterministic
  fixture prices, set new UTC simulation-generation timestamps and preserve
  instruments/accounts/holdings/trades. A refresh generates a new simulated
  observation; it does not represent an exchange trade or change DNSE timestamps.
  Reject non-advancing clock values rather than silently reusing a timestamp;
  all accepted refreshes must invalidate earlier preview timestamps.
- Display **Simulation / generated**, generation time and **Change vs scenario
  reference**. Do not call this DNSE/live data or today's actual market change.
  A quote older than 900 seconds is still stale; after a refresh the investor
  must preview again before confirmation. Preserve the M2 seed fixture unchanged.

No account credentials are created by `init-demo`; registration supplies the
one-time capital. SETUP owners may add explicitly fake test accounts via the
account service. The new settings/commands belong in SETUP only when implemented
and verified, so the current working M2 setup remains executable meanwhile.

### 7.4 Requests, responses and rejection examples

New designed endpoint: POST `/api/simulation/quotes/refresh`, authenticated
Investor, simulation mode only, `{}` body and `X-CSRF-Token` header.

```json
{"source":"simulation","generated_at":"2026-10-10T09:00:00.000001Z","updated":12}
```

Return 200 for that response. Return 401 `AUTH_REQUIRED`, 403 `CSRF_FAILED` or
`ACCOUNT_DISABLED`, 403 `SIMULATION_DISABLED` for wrong mode/mixed sources,
409 `SIMULATION_CLOCK_NOT_ADVANCED` for a non-advancing clock, 422
`VALIDATION_ERROR` for unexpected input, or 503 `SERVICE_UNAVAILABLE` for storage
failure. Clock/mode/source/storage errors leave every row unchanged.

Example visible mode error: "Demo quote generation is unavailable in this mode.
Ask the operator to start the local simulation setup." Clock error: "A new demo
timestamp could not be generated. Wait a moment and try again."

Preview a buy with `{"side":"buy","symbol":"HPG","quantity":1000}`. At
28,000 VND and 100,000,000 cash, return `estimate_vnd:28000000`,
`can_submit:true`, plus `quote.source:"simulation"` and the actual generated
`quote.quoted_at`. Submit to `/api/orders/buy`:

```json
{"symbol":"HPG","quantity":1000,"expected_quote_at":"2026-10-10T09:00:00.000001Z"}
```

If accepted, return section 5's 201 result: 72,000,000 cash and 1,000 HPG. If a
refresh happened after preview, return 409 `QUOTE_CHANGED`: "Price changed;
refresh the preview. Check the new price before confirming your order." If the
timestamp is older than 900 seconds, return 409 `QUOTE_STALE`: "This quote is
over 15 minutes old. Generate demo quotes, then preview your order again."
In DNSE mode advise waiting for a fresh feed quote instead; never expose a demo
refresh as the cure for a provider outage. Existing section 5 shortage/quantity
errors and section 6 portfolio ownership/valuation rules remain unchanged.

Required implementation checks: repeat preview writes nothing; two competing
orders cannot overspend/oversell; rejected orders roll back; partial/full sales
conserve cost basis; old previews fail after refresh; wrong mode/mixed DB refresh
changes nothing; DNSE timestamps survive; a new user completes registration →
generate simulated quotes → buy → portfolio → sell using visible navigation.
These checks are acceptance work for #76/#79/#82, not tests already run here.

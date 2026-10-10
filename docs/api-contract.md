# Application API contract

Owner: @bianh13, #49. Design revision: 3 October 2026. Review: @VuSiSi.

This is an implementation handoff, not a claim that all routes run. On `main`,
only GET `/` (302 to `/market`) and GET `/market` (200/503 HTML) are implemented.
The resumed PR #60 implements the quote list JSON endpoint and modular DNSE worker;
authentication/subscription was verified, while actual quote/unit comparison and review remain pending. All other endpoints below
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
| GET | `/api/market/quotes` | G/U; US03 | no parameters | 200 quotes array; price/reference/time/source/stale/change | 503 MARKET_UNAVAILABLE | Implemented in resumed #60; review pending |
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


## Order implementation status — #76

The buy branch implements `/trade`, POST `/api/orders/preview`, POST
`/api/orders/buy` and POST `/api/simulation/quotes/refresh`. They require the
trusted #77 auth/CSRF adapter; without it, private requests fail closed with 503.
This is not completion of the login-to-trade journey. See
[concrete interfaces and remaining integration](order-implementation.md).
Simulation refresh returns 200 source/generated_at/updated; it accepts `{}`
only. Shared auth errors still apply, with 403 SIMULATION_DISABLED for wrong
mode/source, 409 SIMULATION_CLOCK_NOT_ADVANCED, 422 VALIDATION_ERROR and 503
SERVICE_UNAVAILABLE. No broker API is called. Existing exact-money and no-auto-retry
contracts remain binding; sell execution belongs to #79.

# Milestone 3 - VirtuTrade UI

Planning baseline recorded 10 October 2026 against main commit `a7f24e6`.
PO: @bianh13. Sprint 3 SM: @longbk761-bot. This dossier is in progress:
wireframes, implemented journeys and browser evidence are still required.

## 1. P0 stories and status

Statuses describe the observed implementation baseline, not the ambition of an
issue or the existence of a schema. Old M1/M2 issue closure does not prove a
working M3 journey. Feature owners update rows with verified PR/commit evidence.

| Story | Screen(s) | Route | Status | Issue | Note |
| ----- | --------- | ----- | ------ | ----- | ---- |
| US01 - Register / sign in | Register, Login (linked from the market header) | `/register`, `/login` | partly works | [#77](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/issues/77) | |
| US02 - Initial virtual capital | Register → portfolio balance | `/register` → `/portfolio` | partly works | [#78](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/issues/78) | |
| US03 - Find a stock and inspect its quote | Market → search → stock detail | `/market`, `/market/<symbol>` | partly works | [#85](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/issues/85) | Or Market list → stock detail (?) |
| US04 - Buy shares | Market detail → Buy | `/trade?side=buy&symbol=HPG` | not started | [#76](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/issues/76) | Or Stock detail → Trade (?) |
| US05 - Sell shares | Portfolio holding → Sell | `/trade?side=sell&symbol=HPG` | not started | [#79](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/issues/79) | |
| US06 - View portfolio | Navigation → Portfolio | `/portfolio` | not started | [#81](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/issues/81) | Or just Portfolio (?) |
| US10 - Insufficient-balance warning | Buy form → change quantity → preview | `/trade?side=buy` | not started | [#76](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/issues/76) | |

US03 currently renders only a seeded table with a stale-data indicator;
search/detail and the navigation shown below are planned. No other P0 is complete.

Updated screen flow (M1 target refined for M3; only home → market exists today):

### Screen flow (real navigation today, planned navigation dashed)

```mermaid
flowchart TD
    Home[Home /] -->|redirect| Market[Market /market]
    Market --> Login[Login /login]
    Market --> Register[Register /register]
    Login -->|success, today| Market
    Register -->|success, today| Market
    Login -. success, planned .-> Portfolio[Portfolio /portfolio]
    Register -. success, planned .-> Portfolio
    Market -. search / select .-> Detail[Stock detail /market/symbol]
    Detail -. Buy, sign in if needed .-> Trade[Trade /trade]
    Portfolio -. Buy or Sell .-> Trade
    Trade -. confirm .-> Portfolio
    Trade -. rejected: fix input .-> Trade
    Portfolio -. Browse stocks .-> Market
    Portfolio -. Log out .-> Market
    Market -->|Log out| Market
```

Solid arrows exist in `main`; dashed arrows are designed and not yet
implemented.

## 2. Wireframes

ASCII drafts live here so they can be reviewed in the PR diff. Final exports
(photo of paper or PNG) go in `docs/images/ui/` and replace the drafts. Every
screen shares one header: **VirtuTrade · Market · Portfolio · Log in / Register
(guest) or email · Log out (signed in)**.

### 2.1 Register - `/register`

*The user comes here to create a private simulation account and receive
100,000,000 VND of virtual cash.*

**Calls:** `POST /api/accounts` (HTML form posts to `POST /register`, same
service). Pre-auth CSRF token is embedded in the form.

```text
+---------------------------------------------------------------+
| VirtuTrade   Market   Log in                                  |
+---------------------------------------------------------------+
| Create your simulation account                                |
| You receive 100,000,000 VND once.                             |
|                                                               |
| [!] Email already in use            <- on error               |
| [!] Email must be valid             <- on error               |
| [!] Passwords must match            <- on error               |
|                                                               |
| Email                 [______________________]                |
| Password              [______________________]  8-128 chars   |
| Confirm Password      [______________________]                |
| [ Register ]                                                  |
| Already registered? Log in                                    |
+---------------------------------------------------------------+
```

### 2.2 Login - `/login`

*The user comes here to open their own account and see only their own data.*

**Calls:** `POST /api/sessions` (form: `POST /login`).

```text
+---------------------------------------------------------------------------------------------------+
| VirtuTrade   Market   Register                                                                    |
+---------------------------------------------------------------------------------------------------+
| Log in to your simulation account                                                                 |
| [!] Invalid email or password. Five wrong passwords lock the account 15 min.       <- on error    |
| Email     [______________________]                                                                |
| Password  [______________________]                                                                |
| [ Log in ]                                                                                        |
| Already have account? Sign in                                                                     |
+---------------------------------------------------------------------------------------------------+
```

### 2.3 Market list - `/market` (four states)

*The user comes here to find a stock by ticker or company name and see whether
its price is fresh.*

**Calls:** `GET /api/market/quotes` (list; designed, JSON owner agreed with #59/#75).
Until the JSON endpoint lands the page renders the same data
server-side from `market_snapshot`. Search uses `GET /market?q=<text>`.

```text
+- Data -----------------------------------------+  +- Empty (no match) ---------------------+
| Search [HPG___________] [Search]               |  | Search [XYZ___________] [Search]       |
|                                                |  |                                        |
| [ Generate demo quotes ]  (simulation mode)    |  | No stocks match "XYZ".                 |
| Symbol  Price    Change  Quote time    Status  |  | [ Clear search ]                       |
| HPG     28,000   +1.82%  09:15 30/09   Seed    |  +----------------------------------------+
|  Hoa Phat Group                  Price may be  |  +- Empty (no quotes at all) -------------+
|  [ View ]                         delayed      |  | No quotes yet.                         |
+------------------------------------------------+  | Market prices appear when available.   |
+- Loading --------------------------------------+  +----------------------------------------+
| Search [HPG___________] [Search] (kept)        |  +- Error ---------------------------------+
|                                                |  |                                         |
| (spinner) Loading prices...                    |  | Market data is unavailable.             |
+------------------------------------------------+  | Search text kept: [HPG___]              |
                                                    | [ Try again ]  (read-only retry)        |
                                                    +-----------------------------------------+
```

Demo data: while no live DNSE feed exists (#59), the P0 market runs on
labelled simulation data. **Generate demo quotes** appears only in simulation
mode, calls `POST /api/simulation/quotes/refresh` (#75), and the Source column
then reads **Simulation / generated** with the generation time. Seed rows keep
the **Demo / seed** label. Simulated data is never called live DNSE data.

Time zone (**proposal, not yet agreed**): the template shows UTC today. Showing
local time with an explicit zone label, e.g. `09:15 30/09/2026 (UTC+7)`, is the
fix #87 will validate against the running screen. Likewise `?q=` is a proposed
query name until #85 and the API owner confirm it.

Rules: search text is preserved on retry and after a failed load; the retry
button appears for transient read failures only; narrow screens stack each row
as a card so price, time and status stay visible without horizontal scrolling.

### 2.4 Stock detail - `/market/<symbol>`

*The user comes here to understand one stock's price, daily movement and
freshness before deciding to buy.*

**Calls:** `GET /api/market/quotes/{symbol}` (designed).

```text
+--------------------------------------------------+
| < Back to market                                 |
|                                                  |
| HPG - Hoa Phat Group                             |
| 28,000 VND   +1.82% vs previous close (27,500)   |
| Quoted 09:15, 30/09/2026 (time zone: see 2.3)    |
| Source: Demo / seed   [Price may be delayed]     |
|                                                  |
| [ Buy ]   (guest -> sent to Log in first)        |
+--------------------------------------------------+
Unknown symbol:  "Ticker not found"  [ Back to market ]
No reference:    change shown as "Reference unavailable"
```

### 2.5 Trade (buy / sell) - `/trade`

*The user comes here to preview the cost of a virtual order and confirm it.*

**Calls:** `POST /api/orders/preview`, `POST /api/orders/buy` or
`POST /api/orders/sell`. A failed order POST is never auto-retried.

```text
+--------------------------------------------------+
| Buy HPG        Cash: 100,000,000 VND             |
| Quantity [1000]   Quote 28,000 (09:15:00)        |
| Estimated cost: 28,000,000 VND                   |
|                                                  |
| [!] Exceeds available balance by 300,000 VND     |
| [ Confirm buy ] (disabled while warning shows)   |
|                                                  |
| Quote stale: generate demo quotes, preview again |
| Result unknown? "Check your portfolio" - no retry|
+--------------------------------------------------+
```

### 2.6 Portfolio - `/portfolio`

*The user comes here to see cash, holdings, average cost and unrealised P&L.*

**Calls:** `GET /api/portfolio`; Sell links to `/trade?side=sell`.

```text
+--------------------------------------------------+
| Portfolio        Total: 46,600,000 VND           |
| Cash: 40,000,000 VND                             |
| HPG  200 sh  avg 30,000  value 6,600,000         |
|      P&L +600,000 (+10.00%)       [ Sell ]       |
| Empty: "No positions yet" (total = cash)         |
+--------------------------------------------------+
```

## 3. Error messages

Messages are grouped by how far they have actually been built. "Today" is the
exact string produced by `src/virtutrade/accounts/errors.py` and
`src/virtutrade/accounts/service.py`. The **hint** column is a proposal for #87:
the API `message` stays unchanged (it matches US01 and `docs/api-contract.md`,
and existing tests assert it), and the UI may add one recovery line beside it.
API error codes never change.

### 3.1 Implemented and reachable through the UI

| API error code | Business rule | Exact message the user sees today | Recovery hint (proposal, #87) |
| -------------- | ------------- | --------------------------------- | ----------------------------- |
| 409 `EMAIL_IN_USE` | US01 - an email can register only once | Email already in use | Sign in with this email, or register with another one. |
| 401 `INVALID_CREDENTIALS` | US01 - wrong password and unknown email give the same answer | Invalid email or password | Check both fields and try again. |
| 429 `LOGIN_LOCKED` | US01 - five wrong passwords lock the account for 15 minutes | Account locked. Try again in N seconds. (N is the remaining time from the server) | Show the remaining time in minutes and seconds; sign-in works again when it reaches zero. |

### 3.2 Implemented, verified by tests only

| API error code | Business rule | Exact message today | Why it is not shown in the UI |
|----------------|---------------|---------------------|-------------------------------|
| 403 `ACCOUNT_DISABLED` | BR9 - disabled accounts cannot sign in or trade | Account is disabled | No Admin screen exists yet (US13, P1); only a database edit triggers it. |
| 422 `VALIDATION_ERROR` | US01 - email format, password 8..128 characters | Enter a valid email address. / Password must be 8..128 characters. | The browser's own form validation blocks these first; the server message appears only for direct API calls. |

### 3.3 Proposed - not implemented until #76 and #79 merge

| API error code | Business rule | The user sees (target) |
| ---------------- | --------------- | ------------------------ |
| 409 `INSUFFICIENT_CASH` | BR1 - an order may not cost more than the available cash | Insufficient cash: this order needs 360,000,000 VND but only 72,000,000 VND is available. Reduce the quantity and preview again. |
| 409 `INSUFFICIENT_SHARES` | BR2 - a sale may not exceed the shares held | You hold 500 HPG; the maximum you can sell is 500. Reduce the quantity and preview again. |
| 422 `INVALID_QUANTITY` | US04/US05 - quantity is a whole number of at least 1 | Quantity must be a whole number of at least 1 share. Enter a valid quantity and preview again. |
| 409 `QUOTE_CHANGED` | BR3 - the fill uses the quote accepted at submission | Price changed; refresh the preview. Check the new price before confirming your order. |

Rows in 3.3 move to 3.1 only after someone has reproduced them in a browser.
Show lockout time beside the lockout message, place errors next to the relevant
input or in an accessible alert, and never show stack traces, credentials or
session tokens.

## 4. What changed since M2

**Navigation and presentation architecture:** M2 redirects `/` to a standalone
market page. Walking through registration → market → trade → portfolio exposed
the lack of visible entry points for all other P0 stories. The M3 design now adds
register/login and stock-detail page routes plus a shared navigation template;
feature modules keep their own routes/services/repositories and render within
that shared shell. These are designed routes, not implemented endpoints.

The same PR updates `docs/design.md` section 1 with this boundary and route plan.
Authentication/market owners implement it in their issues, and Vu provides the
wireframes. The shared shell must not contain SQL, trading rules or provider keys.

**Shared transaction and simulation proposal - #75:**
[API contract section 7](api-contract.md#7-m3-shared-order-and-simulation-contract--75)
defines the module interfaces and one atomic cash/holding/trade transaction.
The new local-demo flow is Register → Market → **Generate demo quotes** → select
stock → Preview → Confirm → Portfolio. Add the refresh action to the market/trade
wireframes; it calls POST `/api/simulation/quotes/refresh` and appears only in
simulation mode. The UI uses source **Simulation / generated**, generation time
and **Change vs scenario reference**, keeping simulated data distinct from DNSE.

Fixed old seed quotes cannot authorize a trade. Explicit initialization creates
a separate simulation DB; manual refresh generates new labelled observations,
invalidates previous previews and preserves balances/holdings/trades. Never
retimestamp historical provider data. The proposed source constraint/migration,
endpoint and ownership change is documented in design.md in this same PR;
implementation belongs to #76, review/agreement to #75, wireframes to #86.
All story statuses above remain unchanged until the UI actually works.

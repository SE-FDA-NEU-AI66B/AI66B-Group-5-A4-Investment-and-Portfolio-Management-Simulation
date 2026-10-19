# Milestone 3 - VirtuTrade UI

Planning baseline recorded 10 October 2026 against main commit `a7f24e6`.
PO: @bianh13. Sprint 3 SM: @longbk761-bot. This dossier is in progress:
wireframes, implemented journeys and browser evidence are still required.

## 1. P0 stories and status

Statuses describe the implementation observed on `main`, not the ambition of an
issue or the existence of a schema. Old M1/M2 issue closure does not prove a
working M3 journey. Screen names are used consistently below: **Register,
Login, Market list, Stock detail, Trade, Portfolio**. The Notes column
separates what is **implemented on `main`**, what is **planned** (route or
behavior not on `main`) and **open PR work**.

| Story | Screen(s) | Route | Status | Issue | Notes |
| ----- | --------- | ----- | ------ | ----- | ----- |
| US01 - Register / sign in | Register, Login | `/register`, `/login` | partly works | [#77](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/issues/77) | Implemented: both pages, session cookie, CSRF, lockout; both redirect to Market list today. Planned: return to the page the guest came from via a local `next` (proposed), otherwise Portfolio once #81 lands. Open PR: <add number or "none">. |
| US02 - Initial virtual capital | Register | `/register` | partly works | [#78](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/issues/78) | Implemented: 100,000,000 VND granted when the account is created (tested). Planned: balance visible on Portfolio (#81); no screen shows it today. |
| US03 - Find a stock and inspect its quote | Market list, Stock detail | `/market`, `/market/<symbol>` | partly works | [#85](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/issues/85) | Implemented: Market list only. Planned (#85): search (`?q=`, proposed) and Stock detail. Open PR: <add number or "none">. |
| US04 - Buy shares | Stock detail, Trade | `/market/<symbol>`, `/trade?side=buy&symbol=HPG` | not started | [#76](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/issues/76) | Planned: Buy on Stock detail; a guest is sent to Login first. |
| US05 - Sell shares | Portfolio, Trade | `/portfolio`, `/trade?side=sell&symbol=HPG` | not started | [#79](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/issues/79) | Planned: Sell on each Portfolio holding, keeping the symbol in the link. Needs the shared order code from #76 and the Portfolio screen from #81. |
| US06 - View portfolio | Portfolio | `/portfolio` | not started | [#81](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/issues/81) | Planned: a "Portfolio" header link for signed-in users. |
| US10 - Insufficient-balance warning | Trade | `/trade?side=buy&symbol=HPG` | not started | [#76](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/issues/76) | Planned: inline warning on the buy preview. |

On `main` today: `/` redirects to Market list; Register, Login and Log out are
reachable from the Market list header; there is no Portfolio link and no Trade
screen. Everything else in this document is planned.

### Screen flow (solid = on `main`, dashed = planned)

```mermaid
flowchart TD
    Home[Home /] -->|redirect| Market[Market list /market]
    Market --> Login[Login /login]
    Market --> Register[Register /register]
    Login -->|success, today| Market
    Register -->|success, today| Market
    Market -->|Log out| Market

    Market -. "header Portfolio, signed in" .-> Portfolio[Portfolio /portfolio]
    Market -. "header Portfolio, guest" .-> Login
    Market -. "select a stock" .-> Detail[Stock detail /market/symbol]
    Detail -. "Buy, signed in" .-> Trade[Trade /trade]
    Detail -. "Buy, guest" .-> Login
    Login -. "success, came from Buy: back to Trade (local next)" .-> Trade
    Login -. "success, no next" .-> Portfolio
    Register -. "same as Login" .-> Portfolio
    Trade -. "order saved (201)" .-> Portfolio
    Trade -. "rejected or invalid: stay, fix input" .-> Trade
    Trade -. "result unknown: Check your portfolio" .-> Portfolio
    Portfolio -. "Sell on a holding" .-> Trade
    Portfolio -. "header Market" .-> Market
    Portfolio -. "Log out" .-> Market
    Portfolio -. "Buy more" .-> Trade
```

Trade → Portfolio means an order that was **saved**, not a click on Confirm.
A rejected order keeps the user on Trade with the error beside the input.
The `next` value must be a local path (`/trade?...`), never an external URL.

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
| [!] Email already in use            <- on error (today)       |
| [!] Enter a valid email address.    <- on error (today)       |
| [!] Passwords must match            <- proposed, see below    |
|                                                               |
| Email                 [______________________]                |
| Password              [______________________]  8-128 chars   |
| Confirm Password      [______________________]  (proposed)    |
| [ Register ]                                                  |
| Already registered? Log in                                    |
+---------------------------------------------------------------+
```

Confirm Password and its error are proposed; the current form has Email and Password only.

### 2.2 Login - `/login`

*The user comes here to open their own account and see only their own data.*

**Calls:** `POST /api/sessions` (form: `POST /login`).

```text
+---------------------------------------------------------------+
| VirtuTrade   Market   Register                                |
+---------------------------------------------------------------+
| Log in to your simulation account                             |
|                                                               |
| [!] Invalid email or password       <- wrong credentials      |
| [!] Account locked. Try again in N seconds.  <- locked        |
|                                                               |
| Email     [______________________]                            |
| Password  [______________________]                            |
| [ Log in ]                                                    |
| Five wrong passwords lock the account for 15 minutes.         |
| Already have account? Register                                |
+---------------------------------------------------------------+
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

### 2.5 Trade: distinct states, corrected amounts, and sell variants - `/trade`

*The user comes here to preview a virtual order and confirm it. Buy and sell
show separate validation states; an invalid order cannot be confirmed.*

**Calls:** `POST /api/orders/preview`, `POST /api/orders/buy` or
`POST /api/orders/sell`. A failed order POST is never auto-retried.

**Buy, sufficient cash:**

```text
+--------------------------------------------------+
| Buy HPG               Cash: 100,000,000 VND      |
| Quantity [1000]       Quote 28,000 (09:15:00)    |
| Estimated cost: 28,000,000 VND                   |
| [ Confirm buy ]  (enabled)                       |
+--------------------------------------------------+
```

**Buy, insufficient cash (US10 acceptance data):**

```text
+--------------------------------------------------+
| Buy ACB               Cash: 500,000 VND          |
| Quantity [32]         Quote 25,000 (09:15:00)    |
| Estimated cost: 800,000 VND                      |
| [!] Exceeds available balance by 300,000 VND     |
| [ Confirm buy ]  (disabled)                      |
+--------------------------------------------------+
```

**Sell, valid quantity:**

```text
+--------------------------------------------------+
| Sell HPG              You hold: 1,000 shares     |
| Quantity [1000]       Quote 30,000 (09:15:00)    |
| Estimated proceeds: 30,000,000 VND               |
| [ Confirm sell ]  (enabled)                      |
+--------------------------------------------------+
```

**Sell, quantity exceeds shares held:**

```text
+--------------------------------------------------+
| Sell HPG              You hold: 500 shares       |
| Quantity [800]        Quote 30,000 (09:15:00)    |
| Estimated proceeds: 24,000,000 VND               |
| [!] You hold 500 HPG; the maximum you can sell   |
|     is 500                                       |
| [ Confirm sell ]  (disabled)                     |
+--------------------------------------------------+
```

After an order is saved, show its result on the Portfolio page. For example:
"Sold 1,000 HPG at 30,000.  
Proceeds 30,000,000 VND.  
Realised P&L +2,000,000 VND."  
Realised P&L appears only after the order is saved; the preview API does not return it.

Shared states:

```text
Quote stale:     "Generate demo quotes, then preview again"
Result unknown:  "Result unknown. Check your portfolio." (link; no retry)
```

### 2.6 Portfolio - `/portfolio`

*The user comes here to see cash, holdings, average cost and unrealised P&L.*

**Calls:** `GET /api/portfolio`; Sell links to `/trade?side=sell`.

```text
+---------------------------------------------------------------+
| Portfolio        Total: 46,600,000 VND                        |
| Cash: 40,000,000 VND                                          |
| HPG  200 sh           avg 30,000          value 6,600,000     |
|      P&L +600,000 (+10.00%)                                   |
|      [ Sell ] -> /trade?side=sell&symbol=HPG                  |
| Empty: "No positions yet" (total = cash)                      |
+---------------------------------------------------------------+
```

## 3. Error messages

Every row separates two things: the **API message**, which is the exact string
in `docs/api-contract.md` and `src/virtutrade/accounts/errors.py`, and the
**UI hint**, a recovery line shown beside it. The API message never changes;
HTML pages and the JSON API share the same string (`accounts/routes.py`,
`_fail`), and the contract and `tests/test_auth.py` depend on it. API error
codes never change either.

**How the hint is added (proposal, implemented under #87 with #77).**
`_fail()` in `accounts/routes.py` currently passes only `exc.message` to the
template. It also passes `exc.code`. The template shows `error` in the alert as
today, and below it the hint looked up by code from one mapping kept in the
module that owns the page (for example a dict in the accounts module). The JSON
envelope built by `_envelope()` is untouched, so JSON clients never receive a
hint. Required tests: the JSON `message` for each implemented code still equals
the contract string and the body has no hint field; the HTML page contains both
the message and its hint. This section documents the design; none of it is
implemented yet.

Test coverage today: `tests/test_auth.py` asserts the message of
`EMAIL_IN_USE`, `INVALID_CREDENTIALS` and `LOGIN_LOCKED`. It asserts only the
code of `ACCOUNT_DISABLED`, and the `VALIDATION_ERROR` messages have no test.

### 3.1 Implemented and reachable through the UI

| API error code | Business rule | API message (unchanged) | UI hint (proposal, #87) |
| -------------- | ------------- | ----------------------- | ----------------------- |
| 409 `EMAIL_IN_USE` | US01 - an email can register only once | Email already in use | Sign in with this email, or register with another one. |
| 401 `INVALID_CREDENTIALS` | US01 - wrong password and unknown email give the same answer | Invalid email or password | Check both fields and try again. |
| 429 `LOGIN_LOCKED` | US01 - five wrong passwords lock the account for 15 minutes | Account locked. Try again in N seconds. (N is the remaining time from the server) | You can sign in again when the countdown ends. |

### 3.2 Implemented, not reachable as visible text today

| API error code | Business rule | API message (unchanged) | UI hint (proposal, #87) | Why it is not shown today |
| -------------- | ------------- | ----------------------- | ----------------------- | ------------------------- |
| 403 `ACCOUNT_DISABLED` | BR9 - disabled accounts cannot sign in or trade | Account is disabled | This account is disabled and cannot be used to sign in or trade. | No Admin screen exists yet (US13, P1); only a database edit triggers it. The message itself has no test. |
| 422 `VALIDATION_ERROR` | US01 - email format, password 8..128 characters | Enter a valid email address. / Password must be 8..128 characters. | None: the message already states the rule. | The browser's form validation blocks these first; the server message appears only for direct API calls. No test asserts these strings. |
| 403 `CSRF_FAILED` | Every state-changing request needs a valid CSRF token | Invalid or missing CSRF token | Reload the page and try again. | Appears only when a form stays open past its token lifetime (pre-auth tokens last about one to two hours). |
| 401 `AUTH_REQUIRED` | Private routes need a valid session | Authentication required | Sign in again to continue. | Browser pages redirect a guest to Login instead of showing text; the message reaches JSON clients, and the Trade and Portfolio pages once built if a session expires mid-use. |

### 3.3 Proposed - not implemented until #76 and #79 merge

Amounts below are the acceptance fixtures; the screen shows the user's own numbers.

| API error code | Business rule | API message (contract) | UI hint (proposal) |
| -------------- | ------------- | ---------------------- | ------------------ |
| 409 `INSUFFICIENT_CASH` | BR1 - an order may not cost more than the available cash | Insufficient cash: this order needs 360,000,000 VND but only 72,000,000 VND is available | Reduce the quantity and preview again. |
| 409 `INSUFFICIENT_SHARES` | BR2 - a sale may not exceed the shares held | You hold 500 HPG; the maximum you can sell is 500 | Reduce the quantity and preview again. |
| 422 `INVALID_QUANTITY` | US04/US05 - quantity is a whole number of at least 1 | Quantity must be a whole number of at least 1 share | Enter a whole number of 1 or more and preview again. |
| 409 `QUOTE_CHANGED` | BR3 - the fill uses the quote accepted at submission | Price changed; refresh the preview | Check the new price before confirming your order. |
| 409 `QUOTE_STALE` | US03/US14 - a quote older than 15 minutes cannot authorize a trade | Price may be delayed; refresh before trading | Simulation mode: generate demo quotes, then preview again. DNSE mode: wait for a fresh quote, then preview again. |

Rows in 3.3 move to 3.1 only after someone has reproduced them in a browser.
Place errors next to the relevant input or in an accessible alert, and never
show stack traces, credentials or session tokens.

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

### Integration evidence — 18 October 2026 (PR #92 branch)

Real browser navigation, without typed deep links: Home → Market → Buy shares
(guest guard) → Register → Market → Buy shares → shortage/correction → confirmed
purchase → Market → Logout → Login → Market → Buy shares. The test used real
account services, cookie sessions, CSRF and a temporary SQLite simulation DB;
no auth callbacks were replaced. It also verified manual quote refresh and a
server-committed purchase whose response was lost, with submission locked afterward.

US04/US10 remain **partly works** until peer acceptance and the real #81 portfolio
transition. `/portfolio` links appear only when that real GET route is registered;
there is no placeholder portfolio. #86 wireframes remain Vu's PR #96 and are not
claimed complete by this integration note. Auth error messages stay unchanged;
the buy UI adds separate recovery guidance for login, CSRF and disabled accounts.

# Requirements - Investment & Portfolio Management Simulation

Milestone 1 baseline, refined for Sprint 2 on **30 September 2026** (#46).
The two interview-backed personas remain unchanged. Requirements below describe
the product backlog; an accepted specification is not an implemented feature.

**M2 implementation slice:** a public, read-only `/market` page showing at least
10 seeded quotes from a real database. Authentication, trading, administration
and live DNSE ingestion remain designed backlog work. Demo prices are labelled
seed data, never live market data. P0 means essential product scope, not a claim
that every P0 is implemented in M2.

---

## 1. Product vision

For beginners who need a safe way to learn stock trading and investors who
already manage several positions, the Investment & Portfolio Management
Simulation provides a realistic paper-trading portfolio with accurate cost
basis, P&L, transaction history, risk alerts and benchmark comparison, so users
can test decisions with market-referenced prices without risking real money or
manually rebuilding their portfolio in a spreadsheet.

---

## 2. Personas

#### 2.1 Persona
**Thangkaka - 20-year-old beginner who has never invested**

Manages the small amount of money currently available through a banking app.
They have not invested before and do not feel an urgent need to invest, but are
open to learning how stock trading works before deciding whether to invest in
the future.

**Goal:** understand the mechanics of buying and selling stocks and practise
without risking real money.
**Blocked by:** limited experience and uncertainty about what to do when placing
an order; they also want to see the opinions and actions of experienced users.

**In their words:** *"I do not currently need to invest in stocks; I am not
money-hungry and do not have much experience."*

**Technical skill:** very comfortable with mobile and banking applications and
can discover features independently, but primarily uses them for transfers.

**Interview note:** thangkaka, interviewed by Vu (SM) on 15/09/2026 at 10:27.

#### 2.2 Persona
**Khánh - 30-year-old investor who manages a concentrated portfolio**

Has invested independently for five years and usually holds 5–7 stock symbols.
They currently combine a brokerage application with Excel, which means some
portfolio information and calculations still have to be entered manually.
They make decisions mainly from company financial reports and domestic and
global macroeconomic conditions, and they care about whether their portfolio is
beating the market.

**Goal:** understand the final average cost, quantity and P&L of each position,
separate cash and margin results when relevant, review the contribution of each
symbol to NAV, and evaluate portfolio performance against VN-Index over useful
periods.
**Blocked by:** manual data entry and the lack of one practical view combining
technical indicators, foreign net buying, quarterly business results, position
P&L and a what-if view of selling a position.

**In their words:** *"Một ứng dụng mô phỏng đầu tư/quản lý danh mục lý tưởng
đối với tôi cần chính xác và hữu dụng trong thực tiễn."*

**English translation:** *"An ideal investment and portfolio management
simulation must be accurate and useful in practice."*

**Technical skill:** experienced with brokerage and spreadsheet tools and
comfortable interpreting technical and fundamental information.

**Interview note:** Khánh, interviewed by Thành (PO) on 16/09/2026 at 09:20.

**Research note:** The team has four members and this Milestone 1 specification
uses two interview-backed personas: one beginner and one experienced investor.
These two personas cover the agreed user groups for the project.

---

## 3. Scenarios

### Actors and system boundary

| Actor | Kind | Responsibility / boundary |
|-------|------|---------------------------|
| Guest | Human | Browse the public market snapshot and register/sign in |
| Investor | Human | Trade virtual money and review their own portfolio |
| Admin | Human, system management | Enable/disable investor accounts; access audited administration |
| DNSE Websocket API | External Machine User | Supply stock quote events to a backend adapter; not a human persona or an application login account |

Admin is a required system role from instructor feedback, not an invented
interview persona. DNSE is modelled as the external machine actor requested by
the instructor; this specification makes no unverified claim about its transport,
authentication or message schema. Those details require official provider docs
before integration. The app sends no real orders to DNSE.

### S1 — Thangkaka opens a first position safely (core product scenario)

1. Register or sign in; a new account receives exactly 100,000,000 VND once (US01, US02).
2. Open a ticker's quote and inspect price, timestamp and delayed-data warning (US03).
3. Enter a whole-share quantity and preview total cost; an over-budget order shows a warning and cannot be confirmed (US04, US10).
4. Confirm an affordable buy; the backend rechecks cash and records the fill atomically (US04).
5. Open holdings to see quantity, average cost, unrealised P&L and total portfolio value (US06).

### S2 — Khánh reviews and rebalances a holding (core product scenario)

1. Inspect a held ticker's reference price and the portfolio's quantity, average cost and P&L (US03, US06).
2. Enter a sell quantity; reject quantities above the holding, otherwise fill at the quote accepted on submission (US05).
3. Review remaining quantity, cash, realised result and unrealised P&L (US05, US06).
4. Open transaction history to inspect the completed sale (US08, P1 follow-up).

### S3 — Protect an existing position (P1, later implementation)

1. An investor sets stop-loss or take-profit on an existing holding (US07).
2. A valid quote crosses the threshold; the system closes that position once and records the automatic transaction (US07, US08).

### S4 — Review progress and compare results (P2, later implementation)

1. An investor opens performance over the last 7 or 30 days (US09).
2. Compare portfolio and VN-Index returns over the same available dates (US11).
3. Open the leaderboard to see the top 10 and their own rank (US12).

### S5 — Admin manages access (P1, design in M2)

1. A signed-in Admin selects an investor account and disables it (US13).
2. The system records who changed the status and when; the disabled investor cannot trade (US13).
3. Admin re-enables the account without resetting its cash or positions; investors cannot access these controls (US13).

### S6 — Machine User supplies stock prices (P1 integration, design in M2)

1. The backend adapter receives a quote event from DNSE Websocket API and validates its symbol, price and timestamp (US14).
2. A newer valid quote replaces the current snapshot; an invalid, duplicate or older event cannot regress the stored quote (US14).
3. After a disconnect, the last quote and its original timestamp remain visible with a delayed-data warning when stale; the adapter can reconnect without duplicating the snapshot (US14, US03).

**Explicitly deferred interview needs:** social opinions/activity, technical
indicators (MA/RSI/Bollinger), foreign net buying, quarterly reports, NAV
contribution, margin and what-if sale preview. Keep these research findings in
section 2; they are not steps in the committed core scenarios until separate
stories, acceptance criteria and priorities are agreed. Stop-loss, history,
performance, rankings, Admin and live feed stories also remain outside the M2
walking-skeleton implementation.

---

## 4. User stories

| ID | Story | Priority | Points |
|----|-------|----------|--------|
| US01 | Register / log in to a simulation account | P0 | 3 |
| US02 | Receive initial virtual capital when creating an account | P0 | 2 |
| US03 | View the current market price of a ticker | P0 | 3 |
| US04 | Place a market buy order | P0 | 5 |
| US05 | Place a market sell order | P0 | 5 |
| US06 | View portfolio holdings with average cost and unrealised P&L | P0 | 3 |
| US07 | Place a stop-loss / take-profit order | P1 | 5 |
| US08 | View transaction history | P1 | 2 |
| US09 | View portfolio performance over time | P2 | 5 |
| US10 | Receive a warning when an order exceeds available balance | P0 | 2 |
| US11 | Compare performance against a benchmark index | P2 | 5 |
| US12 | View a leaderboard of players ranked by performance | P2 | 3 |
| US13 | Admin enables/disables investor accounts with an audit trail | P1 | 3 |
| US14 | Receive validated stock quotes from the DNSE Machine User | P1 | 5 |

### US01 - Register / log in to a simulation account · P0 · 3 points

**Scenario / actor / entry:** S1.1; Guest; `/`

As a beginner investor, I want to register and sign in to my own simulation account so that my virtual cash and holdings remain private.

**Acceptance Criteria:**

  - Given the email has never been registered, when I enter a valid email + password (>=8 characters) and click register, then the account is created and I'm taken to the logged-in home page
  - Given an active registered account and the correct password, when I sign in, then I reach my own portfolio and see no other account's holdings
  - Given the email already exists in the system, when I try to register again with that email, then the system rejects it with "Email already in use"
  - Given the account already exists, when I enter the wrong password 5 times in a row, then the account is temporarily locked for 15 minutes

### US02 - Receive initial virtual capital when creating an account · P0 · 2 points

**Scenario / actor / entry:** S1.1; new Investor; `/`

As a newly registered user, I want to receive initial virtual capital so I can start planning and trading immediately.

**Acceptance Criteria:**

  - Given the account was just created successfully, when the system initializes the account, then the virtual balance shows exactly 100,000,000 VND
  - Given the account has already received its initial capital, when I check the overview page at any later time, then the balance doesn't change on its own outside of transactions I make

### US03 - View the current market price of a ticker · P0 · 3 points

**Scenario / actor / entry:** S1.2, S2.1, S6.3; Guest/Investor; `/market`

As a user, I want to see a ticker's current price so I can decide whether to buy/sell.

**Acceptance Criteria:**

  - Given ticker X is currently trading, when I search for and open ticker X's detail page, then the system shows the latest matched price, the day's % change, and when the price was last updated
  - Given the reference price hasn't updated in more than 15 minutes, when I open the detail page, then the system shows a "Price may be delayed" warning
  - Given the ticker doesn't exist, when I search for it, then the system shows "Ticker not found"

### US04 - Place a market buy order · P0 · 5 points · Screen: `/trade`

**Scenario / actor / entry:** S1.3–S1.4; Investor; `/trade`

As a first-time investor, I want to buy shares at the current market price so
that I can open a position using virtual money instead of my own.

**Acceptance criteria**

- Given HPG is quoted at 28,000 VND, when I enter 1,000 shares before confirmation, then the estimated cost is exactly 28,000,000 VND and no trade has been recorded.
- Given my cash is 100,000,000 VND and HPG is quoted at 28,000 VND, when I buy
  1,000 HPG, then the order fills at 28,000 VND, my cash becomes 72,000,000 VND
  and I hold 1,000 HPG (BR3).
- Given my cash is 72,000,000 VND, when I try to buy 3,000 FPT quoted at
  120,000 VND, then the order is rejected with the message "Insufficient cash:
  this order needs 360,000,000 VND but only 72,000,000 VND is available" (BR1).
- Given the order form, when I submit a buy for 0 shares, then it is rejected
  with "Quantity must be a whole number of at least 1 share".

### US05 - Place a market sell order · P0 · 5 points · Screen: `/trade`

**Scenario / actor / entry:** S2.2–S2.3; Investor; `/trade`

As an investor holding shares, I want to sell at the current market price so
that I can realise a profit or cut a loss.

**Acceptance criteria**

- Given I hold 1,000 HPG bought at an average cost of 28,000 VND and HPG is now
  quoted at 30,000 VND, when I sell 1,000 HPG, then the proceeds are 30,000,000
  VND, the realised profit is +2,000,000 VND, my holding becomes 0 and my cash
  grows by 30,000,000 VND (BR2, BR3).
- Given I hold 500 HPG, when I try to sell 800 HPG, then the order is rejected
  with "You hold 500 HPG; the maximum you can sell is 500" (BR2).
- Given HPG is quoted at 28,000 VND at 09:15:00 and I submit a sell at
  09:15:03, when the quote changes to 27,500 VND at 09:15:10, then my order is
  filled at 28,000 VND (BR3).

### US06 - View portfolio holdings with average cost and unrealised P&L · P0 · 3 points · Screen: `/portfolio`

**Scenario / actor / entry:** S1.5, S2.1, S2.3; Investor; `/portfolio`

As an investor, I want to see every holding's quantity, average cost and
temporary profit or loss so that I can decide whether to hold, buy more or sell.

**Acceptance criteria**

- Given I hold 200 HPG at an average cost of 30,000 VND and HPG is quoted at
  33,000 VND, when I open my portfolio, then the row shows quantity 200,
  average cost 30,000 VND, market value 6,600,000 VND and unrealised profit
  +600,000 VND (+10.0%) (BR6).
- Given my cash is 40,000,000 VND and I hold 200 HPG quoted at 33,000 VND, when
  the portfolio loads, then the total portfolio value shows 46,600,000 VND
  (cash + market value of holdings) within 2 seconds.
- Given my account holds no shares, when the portfolio loads, then it shows
  "No positions yet" and the total equals my cash only.

### US07 - Place a stop-loss / take-profit order · P1 · 5 points · Screen: `/trade`

**Scenario / actor / entry:** S3.1–S3.2; Investor; `/trade`

As a user with an open position, I want to set a stop-loss/take-profit threshold
so I can limit risk without watching the market constantly.

**Acceptance criteria**

- Given I bought 100 shares of X at a cost basis of 25,000 VND, 
  when I set a stop-loss at the default 5% below cost (23,750 VND), 
  then the system saves the stop-loss order attached to that position.
- Given a stop-loss is set at 23,750 VND,
  when the market price hits 23,750 VND, 
  then the system automatically closes the position and sends a notification with the realized loss.
- Given I set a take-profit at 10% above cost basis, 
  when the price hits that threshold, 
  then the system automatically closes the position and sends a notification with the realized gain.
- Given I hold no position in ticker Y, 
  when I try to set a stop-loss on Y, 
  then the system rejects it with the message "No open position to attach a threshold to".

### US08 - View transaction history · P1 · 2 points · Screen: `/history`

**Scenario / actor / entry:** S2.4, S3.2; Investor; `/history`

As a user, I want to view my transaction history so I can review the orders I've placed.

**Acceptance criteria**

- Given I've made 5 transactions this month, 
  when I open the transaction history page, 
  then the system shows all 5 transactions newest-first, each row with ticker, order type, quantity, fill price, and time.
- Given I have no transactions yet, 
  when I open the history page, 
  then the system shows an empty state "No transactions yet".
- Given the transaction list exceeds 50 rows, 
  when I open the history page, 
  then the system shows the 50 most recent transactions with a "Load more" button.
- Given a position was closed automatically by a stop-loss trigger, 
  when I open the history page, 
  then that row is labelled order type "Stop-loss (auto)", distinct from a sell order I placed myself.

### US09 - View portfolio performance over time · P2 · 5 points · Screen: `/performance`

**Scenario / actor / entry:** S4.1; Investor; `/performance`

As a user, I want to see a portfolio performance chart so I can evaluate my P/L trend over time.

**Acceptance criteria**

- Given I have transaction history over the past 30 days, 
  when I open the performance chart page, 
  then the system plots total portfolio value for each day over that 30-day period.
- Given I select the "last 7 days" range, 
  when the chart reloads, 
  then the time axis shows exactly the last 7 data points.
- Given I started with 100,000,000 VND and my portfolio is worth 108,000,000 VND after 30 days, 
  when I open the performance chart page, 
  then the system displays total growth of +8,000,000 VND (+8%).
- Given I have just created my account and placed no orders, 
  when I open the performance chart page, 
  then the chart shows a flat line at the initial virtual capital of 100,000,000 VND.

### US10 - Receive a warning when an order exceeds available balance · P0 · 2 points · Screen: `/trade`

**Scenario / actor / entry:** S1.3; Investor; `/trade`

As a first-time investor, I want to be warned immediately when an order
exceeds my balance so I do not misclick.

**Acceptance criteria**

- Given my virtual balance is 500,000 VND, when I enter a buy order worth
  800,000 VND before confirming, then the form shows the inline warning
  "Exceeds available balance by 300,000 VND" and disables the confirm button
  (BR1).
- Given an over-budget buy order is showing that warning, when I change the
  quantity so the order total is 500,000 VND or less, then the warning
  disappears and the confirm button re-enables (BR1).

The inline warning improves the form experience; the backend must always enforce BR1 independently, including when the cash balance changes after preview.

### US11 - Compare performance against a benchmark index · P2 · 5 points · Screen: `/performance`

**Scenario / actor / entry:** S4.2; Investor; `/performance`

As an investor holding shares, I want to compare my portfolio's performance
against VN-Index so I know whether I am beating or lagging the broader market.

**Acceptance criteria**

- Given my portfolio value changes from 100,000,000 VND to 108,000,000 VND
  over 30 days and VN-Index changes from 1,000 to 1,050 over those same 30
  days, when I open the performance comparison page, then it shows two lines
  over the same timeframe: portfolio +8.0%, VN-Index +5.0%, and a +3.0
  percentage-point gap (BR7).
- Given my account was opened 12 days ago and does not yet have 30 days of
  portfolio data, when I open the performance comparison page, then both lines
  use those 12 available days and the page shows "Data since account opening"
  (BR7).

### US12 - View a leaderboard of players ranked by performance · P2 · 3 points · Screen: `/leaderboard`

**Scenario / actor / entry:** S4.3; Investor; `/leaderboard`

As an investor holding shares, I want to see a leaderboard so I know where I
rank against other players.

**Acceptance criteria**

- Given there are 12 active accounts and my account is ranked 11th with +8.0%
  performance, when I open the leaderboard page, then it shows the 10 highest
  performing active accounts in descending percentage order and separately
  shows my rank as #11 (BR8).
- Given two active accounts both have +12.0% performance, and one first reached
  +12.0% at 10:00 while the other first reached it at 14:00, when the accounts
  are ranked, then the 10:00 account is listed first (BR8).

---

### US13 - Admin manages investor account status · P1 · 3 points · Screen: `/admin/accounts`

**Scenario / actor / entry:** S5.1–S5.3; Admin; `/admin/accounts`

As an Admin, I want to enable or disable an investor account with an audit trail
so that I can manage system access without altering investment records.

**Acceptance criteria**

- Given an active investor account with 72,000,000 VND and 1,000 HPG, when an Admin disables it, then its status becomes `disabled`, its cash/holdings stay unchanged, and one audit event records admin ID, target ID, old/new status and UTC time (BR9).
- Given a disabled investor with an existing session, when they submit a buy or sell, then the backend returns 403 and no balance, holding or trade changes (BR9).
- Given an ordinary Investor, when they try the administration page or status-change endpoint, then the request returns 403 and creates no status change or audit event (BR9).
- Given that disabled account, when Admin enables it, then trading access returns, another audit event is recorded and the initial 100,000,000 VND grant is not repeated (BR5, BR9).

### US14 - Receive quotes from DNSE Machine User · P1 · 5 points · Backend integration

**Scenario / actor / entry:** S6.1–S6.3; external Machine User; backend adapter (no screen)

As an Investor, I want stock quotes supplied by the DNSE Websocket API Machine
User to be validated and stored so that the reference prices I see have a known
source and update time. The Investor benefits; DNSE is the external machine actor
in the integration scenario, not a human with a login or a portfolio.

**Acceptance criteria**

- Given HPG has a quote at 09:15:00 UTC, when the adapter accepts a valid HPG quote of 28,000 VND at 09:15:05 UTC, then exactly one latest snapshot holds that price, timestamp and source `dnse` (BR10).
- Given that snapshot, when a duplicate or older event arrives, then its price and timestamp remain unchanged and no second snapshot is inserted (BR10).
- Given an event with missing symbol, non-positive/non-integer VND price or invalid timestamp, when the adapter validates it, then no quote row is changed and the rejection is logged without credentials (BR10).
- Given the connection stops after 09:15:05 UTC, when the page is opened at 09:31:00 UTC, then the last quote keeps its original timestamp and shows "Price may be delayed"; reconnecting must not relabel demo data as live data (US03, BR10).

Implementation is deferred beyond the M2 seed-backed route; provider protocol
and credentials must be confirmed from official documentation before coding.

---

## 5. Business rules

| ID | Rule | Worked example |
|----|------|----------------|
| BR1 | An order may not cost more than the available cash balance. | Cash 100,000,000 VND. Buy 1,000 HPG at 28,000 VND = 28,000,000 VND → accepted, cash falls to 72,000,000 VND. Then buy 3,000 FPT at 120,000 VND = 360,000,000 VND → rejected: the order needs 360,000,000 VND but only 72,000,000 VND is available. |
| BR2 | An account may sell at most the quantity it currently holds. Short selling is not allowed. | Hold 500 HPG. Sell 500 → accepted, holding becomes 0. Sell 800 → rejected: "You hold 500 HPG; the maximum you can sell is 500." |
| BR3 | A market order is filled at the latest quoted price at the moment the order is submitted. | FPT is quoted at 120,000 VND at 09:15:00; the order is submitted at 09:15:03; the quote moves to 121,500 VND at 09:15:10. Buying 100 FPT costs 12,000,000 VND (filled at 120,000), not 12,150,000 VND. |
| BR4 | A stop-loss order triggers automatically and closes the entire position as soon as the market price reaches or falls below the threshold. A take-profit order triggers the same way once the price reaches or rises above its threshold. Default thresholds are 5% below and 10% above the average cost basis. | Holding 100 shares of X at a cost basis of 25,000 VND. Stop-loss set at 23,750 VND (−5%). Price reaches 23,750 VND → the system sells all 100 shares for 2,375,000 VND, realizing a loss of 125,000 VND. |
| BR5 | The initial virtual capital is fixed for every new account | Every new account receives exactly 100,000,000 VND. |
| BR6 | Buying more of a symbol already held recalculates the average cost as a weighted average of every purchase. Selling does not change the average cost. | Buy 100 HPG at 28,000 VND (2,800,000 VND), then 100 HPG at 32,000 VND (3,200,000 VND). Total 200 shares for 6,000,000 VND, so the average cost is 30,000 VND - not 32,000 VND. Selling 100 HPG at 35,000 VND still leaves the average cost of the remaining 100 shares at 30,000 VND. |
| BR7 | Portfolio and benchmark returns must use the same start and end dates. The comparison period is the most recent 30 calendar days, or the period from account opening when the account is younger than 30 days. | Portfolio: 100,000,000 VND to 108,000,000 VND from 1–31 March = +8.0%. VN-Index: 1,000 to 1,050 from 1–31 March = +5.0%. The displayed gap is +3.0 percentage points. An account opened on 19 March is compared only from 19–31 March and is labelled "Data since account opening". |
| BR8 | The leaderboard includes active accounts only and sorts by current percentage performance descending. Equal performance is ordered by the earliest timestamp at which that account first reached its current percentage performance. | A +12.0% account that first reached +12.0% at 10:00 ranks above another +12.0% account that first reached it at 14:00. An inactive account at +20.0% is excluded. |
| BR9 | Only Admin can change investor status; disabled accounts cannot trade; status changes are audited without changing cash/holdings. | Disabling an account preserves 72,000,000 VND and 1,000 HPG and rejects its next trade with 403. |
| BR10 | One latest validated snapshot per symbol; only newer provider events can replace it; source and original UTC timestamp are preserved. | HPG 09:15:05 replaces 09:15:00; an event at 09:14:59 cannot overwrite it. |

---

## 6. Screens and flow

### 6.1 Screen table

| Route | Purpose | Access | Priority | Stories |
|-------|---------|--------|----------|---------|
| `/` | Landing page; register or sign in to the simulation | G | P0 | US01, US02 |
| `/market` | Browse reference prices; ticker detail/search remains backlog | G, U | P0 | US03 |
| `/trade` | Place buy/sell orders and set stop-loss / take-profit conditions | U | P0 | US04, US05, US07, US10 |
| `/portfolio` | View holdings, average cost, unrealised P&L and total value | U | P0 | US06 |
| `/history` | View completed and rejected transaction history | U | P1 | US08 |
| `/performance` | View portfolio performance chart and compare with VN-Index | U | P2 | US09, US11 |
| `/leaderboard` | View top players by performance and the current user's rank | U | P2 | US12 |
| `/admin/accounts` | Enable/disable investor accounts with audit | A | P1 | US13 |

**Access:** G = Guest · U = authenticated Investor · A = Admin. US14 is an external machine integration without a UI route.

Screens and transitions below describe the target product. In M2 only `/` redirecting to public `/market` is implemented; all other routes are designed backlog. The traceability table records each story separately.

### 6.2 Flow diagram

The original [M1 screen-flow image](images/screens-flow.png) is retained as historical evidence; the current flow below supersedes it, including Admin and public market access.

Current target screen flow:

```
/ (signed out) --[browse market]------------------> /market
/ (signed out) --[sign in succeeds]---------------> /portfolio
/market        --[select a ticker]----------------> /trade
/trade         --[order filled]-------------------> /portfolio
/trade         --[rejected: insufficient cash]----> /market
/portfolio     --[place another order]------------> /market
/portfolio     --[set stop-loss / take-profit]----> /trade
/portfolio     --[transaction history]------------> /history
/portfolio     --[performance chart]--------------> /performance
/performance   --[ranking]------------------------> /leaderboard
/history       --[back]---------------------------> /portfolio
/performance   --[back]---------------------------> /portfolio
/leaderboard   --[back]---------------------------> /portfolio
/portfolio     --[Admin only: manage accounts]----> /admin/accounts
/admin/accounts --[back]--------------------------> /portfolio
/portfolio     --[sign out]-----------------------> /
```

### 6.3 UML system model

- [Use case diagram source](diagrams/use-case-diagram.puml) and [exported image](diagrams/use-case-diagram.svg)

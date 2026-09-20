# Requirements — Investment & Portfolio Management Simulation

Milestone 1 · Sprint 1 deliverable. Six sections, in this order. A requirement
only counts if it can be checked: every user story below has at least one
acceptance criterion with a concrete number or an exact expected value.

> **Working draft.** Sections marked `TBD` are owned by another member and are
> being written on their own branch. The assembly PR puts all six sections
> together before submission.

---

## 1. Product vision

<!-- TODO @Thanh (PO): one sentence. Who it is for · what problem it removes ·
     why not the obvious alternative (managing a practice portfolio in a
     spreadsheet). Write it after the two interviews are done. -->

TBD — @Thanh.

---

## 2. Personas

<!-- TODO @Vu: Persona 1 — someone who has never invested. Include role, goal,
     what blocks them, one quoted sentence, and the interview note (who was
     spoken to and when). -->

TBD — @Vu.

<!-- TODO @Thanh: Persona 2 — someone with more experience (manages several
     symbols). Same fields, plus the interview note. -->

TBD — @Thanh.

---

## 3. Scenarios

<!-- TODO @Vu: Scenario 1 — opening the first position. 6–10 numbered steps in
     plain language. No screen names, no button names. -->

TBD — @Vu.

<!-- TODO @Thanh: Scenario 2 — comparing the performance of several symbols.
     6–10 numbered steps. No screen names, no button names. -->

TBD — @Thanh.

---

## 4. User stories

| ID | Story | Priority | Points |
|----|-------|----------|--------|
| US01 | TBD — @Vu | | |
| US02 | TBD — @Vu | | |
| US03 | TBD — @Vu | | |
| US04 | Place a market buy order | P0 | 5 |
| US05 | Place a market sell order | P0 | 5 |
| US06 | View portfolio holdings with average cost and unrealised P&L | P0 | 3 |
| US07 | Place a stop-loss / take-profit order | P1 | 5 |
| US08 | View transaction history | P1 | 2 |
| US09 | View portfolio performance over time | P2 | 5 |
| US10 | TBD — @Thanh | | |
| US11 | TBD — @Thanh | | |
| US12 | TBD — @Thanh | | |

### US04 — Place a market buy order · P0 · 5 points · Screen: `/trade`

As a first-time investor, I want to buy shares at the current market price so
that I can open a position using virtual money instead of my own.

**Acceptance criteria**

- Given my cash is 100,000,000 VND and HPG is quoted at 28,000 VND, when I buy
  1,000 HPG, then the order fills at 28,000 VND, my cash becomes 72,000,000 VND
  and I hold 1,000 HPG (BR3).
- Given my cash is 72,000,000 VND, when I try to buy 3,000 FPT quoted at
  120,000 VND, then the order is rejected with the message "Insufficient cash:
  this order needs 360,000,000 VND but only 72,000,000 VND is available" (BR1).
- Given the order form, when I submit a buy for 0 shares, then it is rejected
  with "Quantity must be a whole number of at least 1 share".

### US05 — Place a market sell order · P0 · 5 points · Screen: `/trade`

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

### US06 — View portfolio holdings with average cost and unrealised P&L · P0 · 3 points · Screen: `/portfolio`

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

### US07 — Place a stop-loss / take-profit order · P1 · 5 points · Screen: `/order`

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

### US08 — View transaction history · P1 · 2 points · Screen: `/history`

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

### US09 — View portfolio performance over time · P2 · 5 points · Screen: `/`

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

## 5. Business rules

| ID | Rule | Worked example |
|----|------|----------------|
| BR1 | An order may not cost more than the available cash balance. | Cash 100,000,000 VND. Buy 1,000 HPG at 28,000 VND = 28,000,000 VND → accepted, cash falls to 72,000,000 VND. Then buy 3,000 FPT at 120,000 VND = 360,000,000 VND → rejected: the order needs 360,000,000 VND but only 72,000,000 VND is available. |
| BR2 | An account may sell at most the quantity it currently holds. Short selling is not allowed. | Hold 500 HPG. Sell 500 → accepted, holding becomes 0. Sell 800 → rejected: "You hold 500 HPG; the maximum you can sell is 500." |
| BR3 | A market order is filled at the latest quoted price at the moment the order is submitted. | FPT is quoted at 120,000 VND at 09:15:00; the order is submitted at 09:15:03; the quote moves to 121,500 VND at 09:15:10. Buying 100 FPT costs 12,000,000 VND (filled at 120,000), not 12,150,000 VND. |
| BR4 | A stop-loss order triggers automatically and closes the entire position as soon as the market price reaches or falls below the threshold. A take-profit order triggers the same way once the price reaches or rises above its threshold. Default thresholds are 5% below and 10% above the average cost basis. | Holding 100 shares of X at a cost basis of 25,000 VND. Stop-loss set at 23,750 VND (−5%). Price reaches 23,750 VND → the system sells all 100 shares for 2,375,000 VND, realizing a loss of 125,000 VND. |
| BR5 | TBD — @Vu | TBD |
| BR6 | Buying more of a symbol already held recalculates the average cost as a weighted average of every purchase. Selling does not change the average cost. | Buy 100 HPG at 28,000 VND (2,800,000 VND), then 100 HPG at 32,000 VND (3,200,000 VND). Total 200 shares for 6,000,000 VND, so the average cost is 30,000 VND — not 32,000 VND. Selling 100 HPG at 35,000 VND still leaves the average cost of the remaining 100 shares at 30,000 VND. |

---

## 6. Screens and flow

<!-- TODO @Long: table Route / Purpose / Access (G, U, A) / Priority for at
     least 5 screens, plus the flow diagram saved in docs/images/. Every screen
     must appear in the diagram and be reachable. -->

TBD — @Long.

_Screens referenced by this section's stories so far: `/trade` and
`/portfolio`, both P0 and user-only._

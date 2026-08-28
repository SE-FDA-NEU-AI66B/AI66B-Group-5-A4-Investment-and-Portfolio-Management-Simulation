# Software Process Dossier — A4: Investment Simulation & Portfolio Management

## Section 1 — Chosen process and its position on the spectrum

**(a) The model.** **Incremental development**, with **prototyping as a technique inside** the first two increments (throwaway mockups for the portfolio view and leaderboard).

One cycle = two weeks. **Day 1:** the team re-prioritises `docs/backlog.md`; each item pulled in gets one owner and a written acceptance check. **Days 1–2:** any item touching the valuation engine is specified by its owner as a test case with expected numbers before code is written. **Days 3–9:** owners build on feature branches; every change enters `main` through a reviewed Pull Request. **Day 10:** the increment is merged, the suite runs, the build is tagged. Each cycle ends with a deployable build on `main`, a green test suite over the money-computing functions, an updated backlog, and a dated note in `docs/changelog.md`.

**(b) The position.** About **75% agile with plan-driven milestone gates.** *Frozen all semester:* the domain model (Account, Holding, Transaction, PriceQuote), the valuation rules (average-cost basis; realised vs unrealised P&L), the stack, and the four milestone dates plus the demo. *Re-opened every cycle:* feature scope and priority, UI, the leaderboard ranking rule, non-critical quality attributes. A late change to the valuation core invalidates every stored transaction and every test above it, so it is governed plan-driven; the rest is cheap to change and unknowable until used, so it is governed agile.

## Section 2 — The five diagnostic questions

**1. Stable or volatile?** Mixed. The core — buy/sell at a reference price with virtual cash, report profit and loss — has not changed since the topic sheet, and its accounting rules are standard practice we look up rather than invent. The periphery is volatile: the sheet names a leaderboard but not what it ranks, and the price-update path depends on which free data source stays inside its quota.

**2. Safety or legal impact?** None demanding formal change control. No real money moves, no order reaches a market, no payment or identity data is stored — it is explicitly a simulation, outside financial-services regulation. The surviving obligation is **correctness, not compliance**: a wrong P&L is our dominant defect class (Functional Suitability), so we impose test discipline on the valuation engine instead of document sign-off.

**3. Team size and distribution?** Four members, co-located — one class, one campus, weekly face-to-face plus a group chat. Communication cost is low, so a shared backlog and conversation replace heavy specification. The cost we do carry is bus-factor, which is why PR review is mandatory: at least two members have read every part of the system.

**4. Continuous customer engagement?** No — fixed checkpoints. The instructor is available at the four milestones and the demo, not on demand; this is the strongest force pulling us away from fully agile, since an on-site customer is unavailable. We compensate with proxy users: classmates run each increment's build and their feedback goes into `docs/feedback.md`.

**5. Culture and contract constraints?** The course fixes four milestones and the demo date, so **scope, not schedule, is our variable** — which suits incremental delivery and rules out a single big-bang integration. The repository is accessible to the instructor, and one dossier is submitted per team.

## Section 3 — Critical thinking: risks of the opposite choice

Fully plan-driven (one Waterfall pass, signed off before coding), the biggest risk is that **the valuation specification gets frozen by people who have never implemented one.**

*Mechanism.* The rules hide cases we have not met: a partial sell against multiple buy lots, a sell that empties a holding, ordering of same-day transactions, rounding of a running average cost. These surface only when code meets real transaction sequences. Waterfall defers that to one integration phase near the demo, so each discovery forces an amendment to a signed-off document plus rework above it. With the deadline immovable, the team patches rather than corrects.

*First symptom.* Before the schedule visibly slips, **two numbers that must agree will disagree**: the dashboard's portfolio total will not equal cash plus holdings revalued from the transaction history — and the argument will be about which document is authoritative rather than which line of code is wrong.

## Section 4 — Process rules your team commits to

1. **Every change reaches `main` through a Pull Request approved by another member**, with at least one review comment on the diff; direct pushes to `main` are disabled.
2. **Any function that computes money** — cost basis, realised/unrealised P&L, portfolio total, ranking score — **ships with unit tests in the same PR**, and the suite must pass before merge.
3. **Increments are two weeks.** `docs/backlog.md` is re-prioritised on day 1; any requirement change accepted after an increment starts is recorded in `docs/changelog.md` with its date and reason.
4. **Every increment ends with a tagged release on `main` that runs end-to-end.** An increment with nothing runnable is declared failed at the next planning meeting.
5. **The frozen items in §1(b) change only by unanimous team agreement**, recorded as a dated entry in `docs/decisions.md`.

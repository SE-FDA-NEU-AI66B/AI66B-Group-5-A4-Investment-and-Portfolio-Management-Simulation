# Sprint log

One section per sprint. Fill it in **during** the sprint, not the night before
the milestone deadline - the commit timestamps on this file are part of the
evidence that the process was real.

---

## Sprint 1 - Weeks 5-6 (September 2026)

### Sprint goal

Complete the Milestone 1 discovery and specification package for a paper-trading
simulation, including two real user interviews, personas, scenarios, a
testable requirements baseline and the first performance-related backlog items.

### Required chore issues

| Issue | Owner | Closed? |
|-------|-----------|----------|
| [Chore] Refine backlog cho Sprint 1 (#25) | @bianh13 (PO) | Done |
| [Chore] Sprint 1 wrap-up (#26) | @VuSiSi (SM) | Done |

### Committed

| Issue | Story | Points | Owner |
|-------|-------|--------|-------|
| #13 | US01 - Register / log in to a simulation account | 3 | @VuSiSi |
| #14 | US02 - Receive initial virtual capital | 2 | @VuSiSi |
| #15 | US03 - View the current market price of a ticker | 3 | @VuSiSi |
| #16 | US04 - Place a market buy order | 5 | @nguyentue110 |
| #17 | US05 - Place a market sell order | 5 | @nguyentue110 |
| #18 | US06 - View portfolio holdings with average cost and unrealised P&L | 3 | @nguyentue110 |
| #19 | US07 - Place a stop-loss / take-profit order | 5 | @longbk761-bot |
| #20 | US08 - View transaction history | 2 | @longbk761-bot |
| #21 | US09 - View portfolio performance over time | 5 | @longbk761-bot |
| #22 | US10 - Receive warning when an order exceeds available balance | 2 | @bianh13 |
| #23 | US11 - Compare performance against a benchmark index | 5 | @bianh13 |
| #24 | US12 - View leaderboard ranked by performance | 3 | @bianh13 |

**Total committed: 43 points**

### Result

| Issue | Points | Status | Detail |
|-------|--------|--------|------------------|
| #13 | 3 | Done | US01 acceptance criteria were completed in the Sprint 1 account stories. |
| #14 | 2 | Done | US02 acceptance criteria were completed in the Sprint 1 account stories. |
| #15 | 3 | Done | US03 acceptance criteria were completed in the Sprint 1 account stories. |
| #16 | 5 | Done | US04 acceptance criteria were completed in the Sprint 1 trading stories. |
| #17 | 5 | Done | US05 acceptance criteria were completed in the Sprint 1 trading stories. |
| #18 | 3 | Done | US06 acceptance criteria were completed in the Sprint 1 trading stories. |
| #19 | 5 | Done | US07 acceptance criteria were completed in the Sprint 1 portfolio stories. |
| #20 | 2 | Done | US08 acceptance criteria were completed in the Sprint 1 portfolio stories. |
| #21 | 5 | Done | Performance-over-time story completed in PR #33. |
| #22 | 2 | Done | Balance warning story completed in PR #32. |
| #23 | 5 | Done | Benchmark comparison story completed in PR #32. |
| #24 | 3 | Done | Leaderboard story was completed as part of the Sprint 1 backlog. |
| #25 | 5 | Done | The 12 stories and their acceptance criteria were reviewed and refined before finalizing the Sprint 1 baseline. |
| #26 | 5 | Done | Sprint 1 wrap-up was recorded. |

Supporting tasks completed during the sprint:

- #34 [Task] Interview first-time investor persona — completed as a child task of #22 (US10).
- #35 [Task] Interview investor holding shares persona — completed as a child task of #23 (US11).

**Completed: 43 points. Velocity this sprint: 43**

### Not finished / carried over

- No committed Sprint 1 user story was carried over. The administrative issues #25, #26 and #35 are documented as complete and remain open only until the final documentation Pull Request is merged.

### Sprint Review

- What we demonstrated: The requirements baseline, two interview-backed personas, two scenarios, and acceptance criteria for performance, benchmark comparison and balance warnings.
- Feedback received: The experienced investor needs weighted average cost, per-position P&L, NAV contribution, technical/fundamental context and a what-if sale view. The beginner needs safe practice and confidence before using real money.
- Backlog changes as a result: All 12 Sprint 1 stories are complete. Backlog refinement and both interview-backed personas are included in the final baseline.

### Retrospective

| Keep doing | Stop doing | Start doing |
|------------|------------|-------------|
| Keep the interview answers close to the acceptance criteria. | Avoid leaving ownership and acceptance checks implicit. | Start validating the money calculations with concrete examples before implementation. |

**One concrete action for the next planning cycle (with an owner):** @longbk761-bot will add executable tests for average cost, realised/unrealised P&L and portfolio totals before further UI work.

### Scrum Master Sprint 2 handover

- Confirm the Sprint 2 Scrum Master during Sprint Planning.
- Start Sprint 2 planning from the completed Sprint 1 baseline.
- Remind every owner of the submission deadline and require a reviewer who did not author the Pull Request.
- Capture the post-planning and pre-submission Project Board screenshots.

<!-- A retro that produces no action item is a complaint session.
     Exactly one action, one owner, checked at the next retro. -->

### Attendance

| Member | Planning | Review | Retro |
|--------|----------|--------|-------|
| @bianh13 | Done | Done | Done |
| @VuSiSi | Done | Done | Done |
| @nguyentue110 | Done | Done | Done |
| @longbk761-bot | Done | Done | Done |

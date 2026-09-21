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

### Hai chore issue bắt buộc

| Issue | Người làm | Đã đóng? |
|-------|-----------|----------|
| [Chore] Refine backlog cho Sprint 1 (#25) | @bianh13 (PO) | Done |
| [Chore] Sprint 1 wrap-up (#26) | @bianh13 (SM) | Done |

### Committed

| Issue | Story | Points | Owner |
|-------|-------|--------|-------|
| #21 | US09 - View portfolio performance over time | 5 | @longbk761-bot |
| #22 | US10 - Receive warning when an order exceeds available balance | 2 | @bianh13 |
| #23 | US11 - Compare performance against a benchmark index | 5 | @bianh13 |
| #24 | US12 - View leaderboard ranked by performance | 3 | @bianh13 |
| #25 | Chore - Refine backlog for Sprint 1 | 5 | @bianh13 |
| #35 | Task - Interview investor holding shares persona | 8 | @VuSiSi |
| #26 | Chore - Sprint 1 wrap-up | 5 | @bianh13 |

**Total committed: 33 points**

### Result

| Issue | Points | Status | If not done, why |
|-------|--------|--------|------------------|
| #21 | 5 | Done | Performance-over-time story completed in PR #33. |
| #22 | 2 | Done | Balance warning story completed in PR #32. |
| #23 | 5 | Done | Benchmark comparison story completed in PR #32. |
| #24 | 3 | Carried over | Leaderboard remained in progress at the Sprint 1 review. |
| #25 | 5 | Done | The 12 stories and their acceptance criteria were reviewed and refined before finalizing the Sprint 1 baseline. |
| #35 | 8 | Done | Investor-holding-shares interview was recorded for the requirements baseline. |
| #26 | 5 | Done | Sprint 1 wrap-up was recorded. |

**Completed: 25 points. Velocity this sprint: 25**

### Sprint Review

- What we demonstrated: The requirements baseline, two interview-backed
     personas, two scenarios, and acceptance criteria for performance, benchmark
     comparison and balance warnings.
- Feedback received: The experienced investor needs weighted average cost,
     per-position P&L, NAV contribution, technical/fundamental context and a
     what-if sale view. The beginner needs safe practice and confidence before
     using real money.
- Backlog changes as a result: The leaderboard remains carried over; backlog
     refinement is complete. Retain the third-persona requirement as an open
     submission risk until the instructor confirms the two-persona exception.

### Retrospective

| Keep doing | Stop doing | Start doing |
|------------|------------|-------------|
| Keep the interview answers close to the acceptance criteria. | Avoid leaving
     ownership and acceptance checks implicit. | Start validating the money
     calculations with concrete examples before implementation. |

**One concrete action for the next planning cycle (with an owner):** @longbk761-bot
will add executable tests for average cost, realised/unrealised P&L and
portfolio totals before further UI work.

<!-- A retro that produces no action item is a complaint session.
     Exactly one action, one owner, checked at the next retro. -->

### Attendance

| Member | Planning | Review | Retro |
|--------|----------|--------|-------|
| @bianh13 | Done | Done | Done |
| @VuSiSi | Done | Done | Done |
| @nguyentue110 | Done | Done | Done |
| @longbk761-bot | Done | Done | Done |

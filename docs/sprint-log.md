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
| #25 | Chore - Refine backlog for Sprint 1 | 5 | @bianh13 |
| #35 | Task - Interview investor holding shares persona | 8 | @bianh13 |
| #26 | Chore - Sprint 1 wrap-up | 5 | @VuSiSi |

**Total committed: 61 points**

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
| #35 | 8 | Done | Investor-holding-shares interview was recorded for the requirements baseline. |

Supporting tasks completed during the sprint:

- #34 [Task] Interview first-time investor persona — completed as a child task of #22 (US10).
- #35 [Task] Interview investor holding shares persona — completed as a child task of #23 (US11).

**Completed: 61 points. Velocity this sprint: 61**

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

### Week 6 UML modelling tasks

- #38 - Create UML use-case diagram.
- #39 - Create UML sequence diagram for the buy-order flow.
- #40 - Create UML sequence diagram for the sell-order flow.

<!-- A retro that produces no action item is a complaint session.
     Exactly one action, one owner, checked at the next retro. -->

### Attendance

| Member | Planning | Review | Retro |
|--------|----------|--------|-------|
| @bianh13 | Done | Done | Done |
| @VuSiSi | Done | Done | Done |
| @nguyentue110 | Done | Done | Done |
| @longbk761-bot | Done | Done | Done |

## Sprint 2 - Milestone 2

Planning recorded: **30 September 2026**. Remaining work window: **30 September–4 October 2026** (UTC+7).
LMS deadline: **5 October 2026 at 00:00**; internal submission-package handoff: **4 October at 20:00**.

**Product Owner / lead developer:** @bianh13. **Scrum Master:** @nguyentue110, succeeding @VuSiSi from Sprint 1.

### Sprint goal

Correct the scenario/story baseline from the instructor's feedback, document how
the system is built, and deliver one real `/market` slice from browser through
backend and database, seeded with at least 10 rows, with a guide verified on
another person's machine. The API design covers all P0 stories; implementing
all those endpoints is not the Milestone 2 walking-skeleton commitment.

### Committed work / initial planning baseline

[Milestone and assigned issues](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/milestone/1) · [Group 5 board](https://github.com/orgs/SE-FDA-NEU-AI66B/projects/7).
Estimates are initial planning values; the SM records any later scope or estimate changes.

| Issue | Deliverable | Points | Owner | Planned reviewer | Internal due (UTC+7) |
|-------|-------------|--------|-------|------------------|---------------------|
| #46 | [Chore] Refine backlog for Sprint 2: scenarios, stories, Admin, DNSE Machine User | 5 | @bianh13 | @nguyentue110 | 01 Oct |
| #47 | Architecture, system boundary and two ADRs; design sections 1 and 5 | 3 | @VuSiSi | @bianh13 | 01 Oct |
| #48 | ERD, data dictionary and business-rule constraints; section 2 | 5 | @bianh13 | @VuSiSi | 02 Oct |
| #49 | API contract and P0 traceability; section 3 | 3 | @nguyentue110 | @VuSiSi | 02 Oct |
| #50 | Implement `/market`, real DB, repeatable seed, config and section 4 | 8 | @bianh13 | @longbk761-bot | 03 Oct |
| #51 | Database-backed integration tests and applicable money regression cases | 3 | @longbk761-bot | @bianh13 | 03 Oct |
| #52 | SETUP, README setup link and independent clean-machine verification | 3 | @longbk761-bot | @VuSiSi | 04 Oct |
| #53 | Readable document/board/app screenshots and final PDF package | 3 | @VuSiSi | @nguyentue110 | 04 Oct |
| #54 | [Chore] Sprint 2 wrap-up and contribution evidence | 2 | @nguyentue110 | @longbk761-bot | 04 Oct |

**Workload revision (30 September, PO request):** @bianh13 owns #46/#48/#50 = **18/35 points (51.4%)**; @VuSiSi owns #47/#53 = 6; @longbk761-bot owns #51/#52 = 6; @nguyentue110 owns #49/#54 = 5. Estimates remain unchanged; ownership moved to give the PO roughly half the work.

**Initial committed: 35 points. Completed: 0 points. Velocity to date: 0.**
No implementation or final deliverable is claimed complete at planning time.
Sprint 1 story closures recorded specification work; they do not prove that the
features run. Historical UML tasks #38–#40 are not counted again in this baseline.

### Scope and handoffs

- @bianh13 owns requirements refinement and main implementation. Narrow scenarios
  or add justified stories; preserve the original interview evidence. Resolve the
  mandatory balance-validation behaviour currently split across P0 and P2.
- Add Admin as a human system-management actor and DNSE Websocket API as an
  external Machine User. Mark each feature as designed, implemented or verified;
  seeded prices must not be described as live DNSE data.
- @bianh13 creates the six-section design outline and owns sections 2, 4 and 6.
  @VuSiSi completes sections 1 and 5. @nguyentue110 owns section 3. Rebase and
  edit the assigned sections to avoid overwriting teammates' work.
- Architecture/schema contracts unblock the skeleton. Long may prepare tests
  and SETUP early, but verifies final commands against the working code. Vu or a
  volunteer from another team tests on a different machine; record who, date,
  OS, tested commit, elapsed time and result only after the actual run.
- Vũ captures the board immediately after planning and again on submission day,
  plus readable document screenshots. The final PDF uses merged `design.md`, a
  complete cover, two board screenshots on page 2, and the running skeleton with
  browser address bar on page 3. PO submits the reviewed package to LMS.

The board's existing iteration named “Sprint 2” starts on 16 September and
contains older UML work. All nine new issues now have label `sprint-2`, the
actual board field **Sprint = Sprint 2**, and the M2 milestone, as requested by
the PO. Historical iteration dates are preserved; the M2 milestone and dates
above determine the submission deadline, not that old iteration date range.

### Completion and review evidence

Required before wrap-up: at least **4 merged PRs**, each reviewed by another
person; at least **5 closed issues**; and per member at least **1 merged PR,
1 review given and 1 issue closed**. Both chore issues must be completed and
closed. Formal reviews use GitHub's **Review changes** and include a substantive
comment. Planned reviewers above are assignments, not evidence of reviews given.

| Member | Merged PR | Review given | Closed issue |
|--------|-----------|--------------|--------------|
| @bianh13 | Pending | Pending | Pending |
| @VuSiSi | Pending | Pending | Pending |
| @nguyentue110 | Pending | Pending | Pending |
| @longbk761-bot | Pending | Pending | Pending |

The SM updates completed points and velocity from actual DoD evidence during the
sprint, records unfinished work and review feedback, and closes #54 through the
final reviewed wrap-up PR. Daily entries are three truthful sentences per member
and committed on the day written; do not write a week's entries in one commit.

### Implementation update — 30 September

The PO's #46/#48/#50 work now includes refined requirements/traceability,
Admin and DNSE Machine User modelling, an ERD matching six created tables,
and a Flask `/market` route reading 12 seeded quotes from SQLite. Local tests
pass for seed idempotence, persistence, rendering, empty/error states and quote
constraints. The setup draft is implementation handoff for Long to verify.

These items remain open pending peer review, merge and remaining screenshot
evidence; **completed points and velocity remain 0** under the team's DoD.
Architecture/ADRs (#47), final API contracts (#49), Long's tests/independent
setup verification (#51/#52), final screenshots/PDF (#53), wrap-up (#54) and
LMS submission remain assigned work. Review/retro results are recorded only
after those events occur.

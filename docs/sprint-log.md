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

### Required chore issues

| Issue | Owner | Closed? |
|-------|-------|---------|
| [Chore] Refine backlog for Sprint 2 (#46) | @bianh13 (PO) | Done (closed 04 Oct) |
| [Chore] Sprint 2 wrap-up (#54) | @nguyentue110 (SM) | Open (closes with this wrap-up PR) |

### Committed

| Issue | Story / Task | Points | Owner |
|-------|--------------|--------|-------|
| #46 | Chore - Refine backlog for Sprint 2 | 5 | @bianh13 |
| #47 | Task - Architecture, Admin/Machine User boundary and two ADRs | 3 | @VuSiSi |
| #48 | Task - ERD and data dictionary with business-rule constraints | 5 | @bianh13 |
| #49 | Task - API contract and P0 traceability | 3 | @bianh13 |
| #50 | Task - Build /market walking skeleton with real seeded database | 8 | @bianh13 |
| #51 | Task - Verify database-backed skeleton and regression cases | 3 | @longbk761-bot |
| #52 | Task - SETUP guide and independent clean-machine verification | 3 | @longbk761-bot |
| #53 | Task - Readable screenshots and Team05_M2.pdf submission package | 3 | @VuSiSi |
| #54 | Chore - Sprint 2 wrap-up | 2 | @nguyentue110 |
| #56 | Task - Review and test ERD; redesign if needed | 5 | @nguyentue110 |
| #59 | Story - Integrate DNSE realtime stock quotes (US14, added scope mid-sprint) | 5 | @bianh13 |

**Total committed: 45 points** (planning baseline 40 + mid-sprint addition #59 worth 5).

**Scope decision - 4 October 2026 (PO):** #59 is unfinished and carried over to
Sprint 3, retaining its 5-point estimate, owner @bianh13, acceptance criteria
and Definition of Done. Historical Sprint 2 commitment remains **45 points**;
the remaining M2 delivery scope is the **40-point baseline**. #59 contributes
**0 completed points / 0 velocity points to Sprint 2**, with **5 points carried
over**. Do not remove it from the historical committed table above or count
it as completed merely because its board iteration changed.

The live issue is Open, labelled `sprint-3` and `carried-over`, assigned to the
existing Sprint 3 board iteration and removed from the M2 milestone. There is
no Sprint 3 milestone/deadline yet. At the PO's follow-up request, PR #60 is
temporarily closed without merging; its branch `feature/dnse-market-data`, code
and unchecked acceptance/DoD requirements are retained for reopening in Sprint 3. Required M2
setup, independent verification and submission work continue in Sprint 2.

[Milestone and assigned issues](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/milestone/1) · [Group 5 board](https://github.com/orgs/SE-FDA-NEU-AI66B/projects/7).
Estimates are initial planning values; the SM records any later scope or estimate changes.

**Task priority correction:** P0 = immediate prerequisites for a coherent,
runnable and reproducible slice (#46, #48, #50, #52); P1 = work to finish alongside
or after that baseline (#47, #49, #51, #53, #54, #56). All ten tasks remain in M2;
P1 does not waive a submission requirement. These task labels describe execution
order and do not change the product-story priorities in requirements.md. No
current committed task is classified P2. Owners and estimates are unchanged.

Original planned reviewers and internal dues (UTC+7): #46→@nguyentue110/01 Oct; #47→@bianh13/01 Oct; #48→@VuSiSi/02 Oct; #49→@VuSiSi/02 Oct; #50→@longbk761-bot/03 Oct; #51→@bianh13/03 Oct; #52→@VuSiSi/04 Oct; #53→@nguyentue110/04 Oct; #54→@longbk761-bot/04 Oct; #56→@bianh13/02 Oct; #59→reviewer TBD (PR #60 draft).

**Current review rotation (PO confirmation, 4 October):** Long reviews Tue;
Tue reviews Thanh; Thanh reviews Vu; Vu reviews Long. Apply this to remaining
PRs: #46 and the eventual #59/PR #60 review go to Tue, #51/#52 to Vu, #53 to
Thanh, and #54 to Long. Existing completed reviews remain valid historical evidence.

**Latest workload revision (30 September, PO request):** @bianh13 owns #46/#48/#49/#50 = **21/40 points (52.5%)**; @VuSiSi owns #47/#53 = 6; @longbk761-bot owns #51/#52 = 6; @nguyentue110 owns #56/#54 = 7. API contract #49 moved to the PO; new #56 adds 5 points for independent ERD testing and possible redesign. Existing estimates remain unchanged; this supersedes the previous 18/35 split.

**Initial committed: 35 points; added ERD review: 5; planning baseline: 40 points; mid-sprint addition #59: 5 points; historical committed scope: 45 points; 4 October carry-over to Sprint 3: 5 points. Completed and velocity live in Result below.**
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
  @VuSiSi completes sections 1 and 5. @bianh13 now owns section 3;
  @nguyentue110 independently reviews/tests section 2 and may redraw the ERD (#56). Rebase and
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
contains older UML work. All ten M2 issues now have label `sprint-2`, the
actual board field **Sprint = Sprint 2**, and the M2 milestone, as requested by
the PO. Historical iteration dates are preserved; the M2 milestone and dates
above determine the submission deadline, not that old iteration date range.

### Result

The completion figures and other issue rows below are the previous SM snapshot,
pending final reconciliation in #54. The 4 October #59 carry-over decision is
updated here immediately; it does not certify completion of other open work.

| Issue | Points | Status | Detail |
|-------|--------|--------|--------|
| #46 | 5 | Done | Closed 04 Oct; PR #55 merged 30 Sept + reviewed; refinement on main |
| #47 | 3 | Done | Closed 03 Oct; PR #63 merged + APPROVED by @bianh13 |
| #48 | 5 | Done | Closed 03 Oct; ERD/dictionary on main + #56 review found model suitable |
| #49 | 3 | Done | Closed 03 Oct; PR #64 merged 04 Oct + APPROVED via Review changes |
| #50 | 8 | Done | Closed 03 Oct; skeleton on main (PR #55/#67) + reviews; verification limits noted under #51 |
| #51 | 3 | Closed 04 Oct WITHOUT full AC evidence | Regression tests live in OPEN PR #68 (unreviewed, unmerged); all AC boxes unchecked — NOT counted; SM recommends reopening until #68 merges |
| #52 | 3 | Closed 04 Oct WITHOUT full AC evidence | SETUP Tested-by still placeholder — NOT counted; SM recommends reopening until a real run is recorded |
| #53 | 3 | Open | PDF submission unconfirmed at wrap-up time |
| #54 | 2 | Open | Closes with this wrap-up PR; counts on merge |
| #56 | 5 | Done | Merged PR #61 on 30 Sept, reviewed by @bianh13; closed 30 Sept |
| #59 | 5 | Carried over to Sprint 3 | PO decision, 4 Oct; 0 completed points in Sprint 2 |

**Completed to date (SM proposed, pending PO confirmation in review): 29 points (#46, #47, #48, #49, #50, #56) + 2 (#54 on merge of this PR) = 31. Velocity: 31 proposed. Excluded: #51, #52 (AC evidence incomplete — see flags above), #53 (PDF unconfirmed), #59 (carried, 0).**

### Not finished / carried over

- **Confirmed carry-over, 4 October:** #59 / PR #60 moves to Sprint 3, 5 points,
  owner @bianh13. The PO reports having a key; the reason for deferral is to
  prioritize required M2 delivery, not waiting for key issuance. Live DNSE
  verification, integration with main's modules and independent review remain
  unfinished. Keep all acceptance criteria and the Definition of Done.
- The SM finalizes any other unfinished work at sprint end using actual evidence.
- **Open follow-up #68** (Long, money regression tests, PR #68 open unreviewed): merges after M2 only if time permits, else Sprint 3; it does not retroactively complete #51.
- **#53 PDF package**: if the PDF is not confirmed submitted, it becomes the top carry-over concern for the PO; SM does not mark it complete without LMS confirmation.

### Sprint Review

- What we demonstrated: Pending — recorded after the Sprint Review.
- Feedback received: Pending as a meeting record. PR-level review record (verifiable now): 10 merged Sprint-2 PRs each carry a non-author APPROVED review via Review changes; substantive comment threads on #66/#67 (schema/module feedback) and #60 (schema scope Q&A).
- Backlog changes as a result: Pending.

### Retrospective

Pending — recorded after the retrospective. Required: one concrete action with one owner. (If no retro is held, the SM records that explicitly instead of inventing one.)

### Completion and review evidence

Required before wrap-up: at least **4 merged PRs**, each reviewed by another
person; at least **5 closed issues**; and per member at least **1 merged PR,
1 review given and 1 issue closed**. Both chore issues must be completed and
closed. Formal reviews use GitHub's **Review changes** and include a substantive
comment. Planned reviewers above are assignments, not evidence of reviews given.

| Member | Merged PR | Review given | Closed issue |
|--------|-----------|--------------|--------------|
| @bianh13 | #55, #57, #58, #64, #66, #67 (all reviewed + merged) | APPROVED on #61, #63 via Review changes | #47 (closed 03 Oct; note: assigned to @VuSiSi) |
| @VuSiSi | #63 (architecture + ADRs, merged) | APPROVED on #65 via Review changes | None — closes #53 when the PDF package lands |
| @nguyentue110 | #61 (erd-review + 26 tests), #62 (sprint-log evidence), both merged | APPROVED on #55, #57, #58, #64; COMMENTED + APPROVED on #66, #67, all via Review changes | #46, #48, #49, #50, #56 (closed after verification) |
| @longbk761-bot | #65 (SETUP verification, merged) | APPROVED on #62 via Review changes | #51, #52 (closed 04 Oct — AC evidence incomplete, see flags in Result) |

**Evidence update — 1 October (SM):** @nguyentue110's row above is verified —
PR [#61](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/pull/61)
merged 30 Sept with APPROVED review by @bianh13; reviews given on
[#55](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/pull/55),
[#57](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/pull/57) and
[#58](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/pull/58);
issue [#56](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/issues/56)
closed 30 Sept. Other members' rows stay Pending until their DoD evidence lands.

**Evidence update — 4 October, final reconciliation (SM):** verified on GitHub:
merged Sprint-2 PRs #55, #57, #58, #61, #62, #63, #64, #65, #66, #67 (10 total,
each with a non-author APPROVED review via Review changes; #66/#67 also carry
substantive COMMENT threads); closed issues #46, #47, #48, #49, #50, #51, #52,
#56 with closers/closures recorded above. Gaps flagged, not hidden: #51 closed
with all AC boxes unchecked while its regression tests sit in open PR #68
(0 reviews); #52 closed while SETUP Tested-by is still a placeholder; #53 open
with PDF submission unconfirmed; @VuSiSi has no issue closure yet (needs #53).
PR #60 (draft) was closed unmerged as part of the #59 carry-over. Review links:
[#62](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/pull/62),
[#63](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/pull/63),
[#64](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/pull/64),
[#65](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/pull/65),
[#66](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/pull/66),
[#67](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/pull/67).

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
Architecture/ADRs (#47), PO-owned final API contracts (#49), Tuệ's ERD review/redesign (#56), Long's tests/independent
setup verification (#51/#52), final screenshots/PDF (#53), wrap-up (#54) and
LMS submission remain assigned work. Review/retro results are recorded only
after those events occur.

DNSE realtime integration will be owned by @bianh13 in a later work session.
The 3 points in #49 cover API design/P0 traceability only; realtime adapter
implementation has not started and is not silently included in that estimate.

### Attendance

| Member | Planning | Review | Retro |
|--------|----------|--------|-------|
| @bianh13 | TBD — SM to confirm | Pending | Pending |
| @VuSiSi | TBD — SM to confirm | Pending | Pending |
| @nguyentue110 | TBD — SM to confirm | Pending | Pending |
| @longbk761-bot | TBD — SM to confirm | Pending | Pending |

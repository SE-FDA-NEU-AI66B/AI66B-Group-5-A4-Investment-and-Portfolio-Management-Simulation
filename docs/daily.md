# Daily

**Optional.** Teams that maintain a daily log should record updates here.

Rule: each member writes three sentences and **commits on the day of writing**;
do not combine a whole week into one commit. The file history is evidence that
the team worked continuously.

---

## 2026-09-30

- @bianh13 — Updated Scenarios and User Stories today, added Admin and DNSE Machine User roles, and labeled/assigned Sprint 2 fields across 10 issues (my scope accounts for 21/40 story points).
Built the ERD/schema for 6 tables and implemented the market page to read 12 seed rows from SQLite. Verified idempotent seeding, data persistence across restarts, and empty/error states with passing tests.
Next steps: Collect team reviews so Vu can finalize the architecture/ADRs and diagrams, Long can run independent SETUP/testing, and Tue can test or redraw the ERD and handle the wrap-up; meanwhile, I will pick up the API integration in the next phase ahead of the deadline.

---

## 2026-10-01

- @nguyentue110 — Today: reviewed the full Milestone 2 scope and team issues, and checked Thanh's PR #60 (DNSE draft). Result: finished the SM tracking table (daily/PR/review/issue) and confirmed the PR #60 schema falls under my #56 review scope. Blocked: PR #60 is stuck on credentials so the review cannot finish yet; waiting on Long/Vu for progress on #51/#52/#47/#53.

---

## 2026-10-03

- @bianh13 — Completed the P0 API contract and scenario-to-endpoint traceability, including access rules, request/response examples and trade rejection cases.
Resolved the ERD cost-allocation question, checked a separate clean clone, and packaged the market page into route/service/repository/template/style modules with 34 tests and lint passing.
Next I need peer approval, Long's independent-machine verification and the address-bar screenshot; I reviewed the DNSE Python SDK, but optional live-feed issue #59 stays deferred while required M2 deliverables take priority.

---

## 2026-10-04

- @bianh13 — Moved unfinished DNSE issue #59 to Sprint 3 and temporarily closed PR #60 while retaining its branch/code, five-point estimate and all acceptance/DoD requirements.
Recorded the carry-over without rewriting Sprint 2's 45-point historical commitment or adding unfinished work to completed points, and synchronized the agreed review rotation.
Prepared the final #46 refinement handoff for Tue's review while independent SETUP evidence, submission packaging and the SM wrap-up remain tracked separately.

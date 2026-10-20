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
Strengthened the market layers and moved the application into src/virtutrade with a package CLI, synchronized SETUP/CI and a fresh-environment check; independent verification must identify the final tested commit.


---

## 2026-10-10

- @bianh13 — Refined the M3 backlog into sixteen deliveries totalling 52 points, with 13 points per member and Long as Sprint 3 Scrum Master.
Mapped every P0 story to an owner and UI entry point, drafted the four-section UI dossier and documented the shared navigation design change while keeping unbuilt features marked incomplete.
After drafting #75, I resumed #59 and verified DNSE authentication/subscription, then implemented and tested buy transactions, the preview form and explicit simulation quotes; live quote comparison, actual auth integration and peer reviews remain pending.

## 2026-10-18

- @bianh13 — Integrated the current auth module with the buy branch, preserved quote/financial checks and separated the optional DNSE worker from the simulation demo.
Verified real registration/login, CSRF/session rejection, persisted purchases and ambiguous-response handling with automated tests and a real browser, while portfolio acceptance remains with #81.
Reconciled PO planning and contract evidence, resolved the feed branch conflicts and repeated a read-only DNSE probe that authenticated/subscribed but received no quote, leaving live price comparison and peer acceptance pending.

## 2026-10-19

- @bianh13 — Fixed the browser QA credential-scanner false positive in PR #92, reran both real-browser scenarios and verified passing GitHub checks.
Observed real HPG/FPT ticks through the read-only DNSE worker, checked persisted quotes via the market API and verified data preservation across a controlled stop/reconnect and app recreation.
After #92 and #96 merged, reconciled #60 and #97 against current main while retaining the provider module, buy/auth behavior and reviewed wireframes; provider-board comparison, final portfolio integration and independent acceptance remain pending.

#### Existing teammate entry from PR #98

- @nguyentue110 — Rebased the #79 sell slice onto `main` after #92 merged and retargeted PR #98 to `main`.
Ran a real-browser sell journey through registration, a buy, a partial sale, an oversell warning and a full sale, saving both screenshots under `docs/images/ui/`.
Updated `docs/ui.md` and traceability for US05; a Sell link from a holding still waits for the Portfolio screen in #81.

#### Existing teammate entry from PR #99

- @nguyentue110 — Brought the #78 grant display onto `main` after the earlier slice landed only on the old auth branch, keeping the one-time grant unchanged.
Expanded the grant tests for client-supplied balance fields and captured a real-browser screenshot of the Market-header balance after registration and login.
The Portfolio balance and independent verification remain pending #81/#83.

## 2026-10-20

- @bianh13 — Verified the reviewed and merged #75 contract against its remaining checklist and reconciled my outstanding acceptance work.
Extended the real-auth buy browser checks with saved evidence and stale-quote recovery, then fixed the stuck loading status and obsolete cash estimate discovered during those checks.
Synchronized the buy error documentation, added the PO-authorized #101 presentation and browser checks, reviewed #104's integration conflicts, and addressed #106/#107 with explicit quote-timing criteria and matching quantity validation, while retaining the Portfolio handoff, independent review and DNSE board-comparison requirements.

- @nguyentue110: Fixed the #105 US01 defect by sending form login to the Portfolio whenever the real GET route is registered, keeping `/market` as the fallback until #81 merges, and added a regression test in `tests/test_auth.py`.
Updated the design, UI and traceability notes; Portfolio screenshots and independent acceptance remain with #81/#82.

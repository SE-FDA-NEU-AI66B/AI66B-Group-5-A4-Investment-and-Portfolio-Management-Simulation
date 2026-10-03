# PO completion handoff - 3 October 2026

Owner: @bianh13. This records artifact delivery and actual checks; it does not
replace reviewer acceptance, independent-machine evidence or the team's DoD.

| Issue | Delivered evidence | Remaining closure evidence |
|-------|--------------------|----------------------------|
| #46 backlog refinement | requirements.md, scenario/story mapping in traceability.md, Admin/US13, DNSE/US14, use-case source/export, design section 6 and SM name; merged PRs #55/#58 | Reviewer acceptance of the final package and applicable clean-machine DoD evidence; remains open |
| #48 ERD/dictionary | design section 2 and schema/ERD in #55; independent keep-model review and 26 constraint tests in #61; money-rules.md resolves F10 and records F1/F2 boundaries | Peer approval/merge of the rounding decision and final acceptance |
| #49 API/P0 mapping | design section 3 inventory of 11 endpoints; api-contract.md examples/access/errors; seven P0 traceability rows | Peer approval/merge; no implementation of all endpoints is claimed |
| #50 walking skeleton | main's Flask/SQLite route, repeatable 12-row seed, real query, config/ignore rules, five integration tests plus 26 ERD tests; SETUP handoff and local clean-clone check below | Actual browser-address-bar screenshot at docs/images/walking-skeleton.png (#53), Long's independent setup verification (#52), final acceptance |
| #59 optional live DNSE | Draft PR #60 contains the worker, JSON/refresh UI, migration and local tests | PO explicitly left this waiting for keys on 3 October; live-provider comparison, integration/conflict resolution and peer review remain pending |

## Clean-clone evidence (same machine, not independent)

- Client date: 3 October 2026; verified baseline commit
  `b5fdb0f8149430f738980300e9bfe81bcf62077f` (main after PR #63).
- Environment: Windows build 26200; Python 3.10.11. A separate clone, new venv,
  copied .env.example and new SQLite DB were used. No developer database changed.
- Installed requirements and pytest/ruff; ran init-db twice: exactly 12 quotes
  each time. GET `/market` returned 200 with 12 symbols and HPG at 28,000 VND.
- `python -m pytest -q`: **31 passed** (0.73 s); `python -m ruff check .`: passed.
  Clone, fresh venv/package install and checks took 33 seconds on this machine.
- The current documentation branch also passed the same 31 tests and lint.
  This is PO-assisted local verification, not a non-author or different-machine run.

## Reviewer walkthrough

1. Match each P0 story (US01-US06, US10) to the endpoint inventory and traceability.
   Check exact requirement messages, quantities, cash and portfolio examples.
2. Check money-rules.md: partial allocation rounds total cost times sold/held
   quantity once; allocated + remaining cost must always equal the original cost.
   The final sale takes the full remaining basis; display rounding is never stored.
3. Run SETUP.md and tests on the reviewer's machine. Record person, date, OS,
   Python version, commit and result in #52; do not copy the author result as yours.
4. For #50/#53, open the running `/market` in a normal browser and capture its
   actual address bar and table. Existing headless page images lack browser
   chrome; do not draw or composite an address bar onto them.
5. Approve/merge only the accepted deliverables. Keep #59 pending until credentials
   and live verification are available; keep API designs distinct from running code.

The current session had no callable Windows computer-use runtime, so it could
not capture the required normal-browser window. That evidence is explicitly open.

# Final retrospective

Five sprints, four members, one live URL. This is what we would carry into the
next team. The detailed lessons with their fixes are in
[operations.md, section 6](operations.md#6-lessons-learned).

## Keep

| Practice | Why it worked | Evidence |
|---|---|---|
| One issue, one branch, one reviewed PR | Every change had a reason, an owner and a second pair of eyes; `scrum-check.yml` enforced it | Sprint 5: every merged PR was reviewed by someone else |
| Tests written from the business rules | BR1-BR3 and the money rules were checked at both sides of each boundary, so later UI work could not break them silently | `docs/testing.md`; 399 tests on `main` |
| A labelled practice market | When the DNSE key failed, the app still worked at any hour, and every simulated price says so on screen | `docs/DNSE.md`; `QUOTE_MODE=simulation` on the VM |
| Browser checks before a release | Playwright scripts caught a broken selector that unit tests could not see (#165, #170) | `scripts/check_*_ui.py` |
| `/health` plus an external monitor | We could prove what was running, and would hear about it if it stopped | `/health` reports the commit; UptimeRobot every 5 minutes |

## Change next time

| What | Instead |
|---|---|
| Deploying on the last day surfaced a setup bug at night (#163) | Deploy in the first days of the sprint, as the brief says |
| Most added Sprint 5 points landed on one person | Spread new work at planning, and pair on late items |
| Branch protection without a required green check | Ask the repository admin to require **Python tests** at the first sprint |

# Operations

How VirtuTrade is released, checked, watched and looked after. Items marked
`TODO(#155)` are filled in after the first deploy and before the `v1.0` tag.

## 1. How to run and release

| | |
|---|---|
| URL | `https://TODO-public-url` (TODO(#155)) |
| Platform | TODO(#155): AWS EC2 with Caddy for HTTPS, or Render free web service |
| Health check | `https://TODO-public-url/health` |
| Data | SQLite in practice-market mode (`QUOTE_MODE=simulation`), sample data and the three README test accounts loaded at start (`init-demo`, `seed-test-accounts`) |
| Release tag | `v1.0` on the commit running at the URL |

**How a new version gets there.** A change reaches the URL only through `main`:
open a pull request, CI runs (section 2), another member approves it, merge, and
the platform deploys the merge commit only after CI on `main` is green.
TODO(#155): on Render, Auto-Deploy is set to "After CI checks pass"; on EC2, a
`deploy` job in `ci.yml` with `needs: python` pulls `main` on the server and
restarts the service. After each deploy, `/health` must return 200 with the new
`commit`.

**Rolling back.** If a release breaks something, run `git revert <merge commit>`
on a new branch, open a pull request and merge it; CI and the normal deploy put
the last good version back, and the history shows what was undone. When the site
is down and cannot wait for CI, redeploy the previous good commit directly
(TODO(#155): Render's **Rollback** on an earlier deploy, or on EC2
`git checkout <previous tag>` and restart the service), then follow up with the
revert so `main` matches the URL again.

## 2. The CI pipeline

`.github/workflows/ci.yml` runs on every pull request and every push to `main`.

| Job / step | What it checks |
|---|---|
| Detect stack | Finds `pyproject.toml`, so the Python job runs; there is no `package.json`, so the Node job is skipped |
| Python: install | `pip install -e ".[dev]"` installs the app and the pinned pytest, pytest-cov and ruff |
| Python: lint | `ruff check .`; a lint error fails the build |
| Python: test | `pytest -v --cov`: every automated test (unit, SQLite repository and Flask route tests) with coverage |
| No secrets committed | A credential pattern scan, and no `.env`, `.sql`, `.sqlite` or dump files in Git |

`scrum-check.yml` adds three checks to each pull request: it links a planned,
typed and assigned issue; someone other than the author must review; and it is
not a draft.

A run takes about 1½–2 minutes (the Python job about 40 seconds of tests).
Latest green run on `main`: [run 41485547732](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/actions/runs/41485547732)
(commit `0e51df1`, 2 November 2026). TODO(#155): replace with the run for the
`v1.0` commit.

**Branch protection.** The `main-protection` ruleset requires a pull request and
blocks force pushes and deletion of `main`. TODO(#155): a repository admin must
also turn on "Require status checks to pass" with **Python tests** selected, then
add the screenshot here.

## 3. Monitoring

**What is logged.** gunicorn writes one access line per request (time, method,
path, status, size) to standard output. The app logs a warning when the market
feed loses its connection, when `/health` fails (exception type only), and when
market data cannot be read. Logs are read in TODO(#155): Render → service →
**Logs**, or on EC2 `journalctl -u virtutrade-web -u virtutrade-feed -f`.

**What is never logged.** Passwords, session cookies and CSRF tokens, request
bodies, email addresses in error messages, DNSE API keys or the provider's error
text (it can echo credentials). Errors use fixed, locally written messages.

**What `/health` checks.** It opens the database read-only and counts stored
quotes: 200 when the count is above zero, 503 when the file is missing,
unreadable or empty. It also reports the quote mode and the running commit.

**The two numbers to watch.**

| Number | How we measure it | When it has gone bad |
|---|---|---|
| Error rate | Share of 5xx lines in the access log | Any 5xx burst, or more than 1% of requests in an hour |
| Response time | Request duration in the access log (gunicorn `%(L)s` field) | Pages slower than 2 s, apart from the first visit after the free host wakes |

A free external monitor (for example UptimeRobot) calls `/health` every 5
minutes and e-mails the team when it is not 200. TODO(#155): set it up after the
first deploy.

## 4. Known risks and technical debt

| Item | Layer | What could happen | Plan |
|---|---|---|---|
| Hosted database resets or lives on one machine | infrastructure | On a free host, accounts and trades vanish when it restarts; on one VM, a disk failure loses them | Accepted: sample data and test accounts reload at start, the README says so, and the VM is backed up weekly (section 5) |
| Shared public test accounts | data | Anyone can trade on them or lock one with five wrong passwords | Accepted: virtual money only, three accounts, a lock lasts 15 minutes and anyone can register |
| Confirm needs the exact previewed quote time | code | With moving prices, "Price changed" makes users preview again | Accepted for v1.0: it stops orders at a price the user did not see; the simulator moves every 20 s |
| Real prices depend on DNSE access | infrastructure | The API key returned 401 on 7 November, and the public chart endpoint is unofficial | Accepted: the hosted app uses the labelled simulator; real data stays documented in `docs/DNSE.md` |
| Browser behaviour is not checked in CI | tests | A chart or watchlist regression passes CI | Playwright scripts in `scripts/` are run before each release; #148 adds an accessibility check |
| A red pull request can still be merged | infrastructure | The ruleset does not yet require a green status check | TODO(#155): repository admin adds the required check |

## 5. Maintenance plan

Owners are proposed by the PO and confirmed at Sprint 5 planning.

| Area | What to do | Owner | How often |
|---|---|---|---|
| Bugs | Triage new `bug` issues, reproduce with a failing test, fix through a reviewed PR | Thanh (triage), area owner (fix) | Weekly, same day for P0 |
| Dependency updates | Check `requirements.txt`, the `dev` extra and the vendored chart library; update one at a time with CI green | Tue | Monthly |
| Backups of the data | Copy the SQLite file off the server (EC2), or confirm that sample data reloads (free host) | Long | Weekly and before every release |
| Monitoring | Read the `/health` monitor e-mails, the 5xx count and the latest CI run on `main` | Vu | Daily in demo week, otherwise weekly |
| Keeping the docs true | Update README, `docs/testing.md` and this file in the same PR as the change (Definition of Done) | Each PR author; Scrum Master checks | Every PR; checked at sprint review |

## 6. Lessons learned

| What happened | What we changed | What we would do differently |
|---|---|---|
| Test evidence drifted from `main`: the M4 dossier listed tests as "Branch" long after they merged, and the final reconciliation (#139) landed hours before the deadline | A checker script (#134) resolves every test named in `docs/testing.md`, and CI runs its test | Update the dossier in the same PR as the test, not at the end |
| Long-lived branches conflicted: the Portfolio PR (#103) sat in conflict and the sell tests (#133) needed several re-reviews | Smaller PRs, an agreed merge order, and rebasing as soon as `main` moves | Open a draft PR on day two of a sprint and merge in small steps every day |
| An outside dependency failed silently: the DNSE key stopped working and we only noticed while building charts | `/health`, a labelled practice simulator, and a credential-free fallback for real data | Check third-party credentials on a schedule from the first day they are used |

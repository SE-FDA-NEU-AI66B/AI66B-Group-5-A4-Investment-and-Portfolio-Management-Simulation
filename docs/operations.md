# Operations

How VirtuTrade is released, checked, watched and looked after. First deployed
on 16 November 2026.

## 1. How to run and release

| | |
|---|---|
| URL | <https://35-206-119-222.sslip.io> |
| Platform | Google Cloud Compute Engine: one `e2-micro` VM (Debian, 30 GB standard disk) inside the always-free tier. Caddy serves HTTPS with an automatic certificate for the `sslip.io` name; gunicorn (1 worker, 8 threads) runs the app on `127.0.0.1:8000`; a separate `virtutrade-feed` service moves the simulated prices. Installed by `deploy/gcp/setup.sh` ([DEPLOY.md](DEPLOY.md)) |
| Health check | <https://35-206-119-222.sslip.io/health> |
| Data | SQLite at `/var/lib/virtutrade/simulation.db` in practice-market mode (`QUOTE_MODE=simulation`). The market and the three README test accounts are created once (`init-demo`, `seed-test-accounts`); accounts and trades stay on the VM disk across restarts and updates |
| Release tag | `v1.0` on the commit running at the URL |

**How a new version gets there.** A change reaches the URL only through `main`:
open a pull request, CI runs (section 2), another member approves it, and it is
merged. There is no automatic deploy job. Once CI on the merge commit is green,
the PO opens SSH from the Compute Engine console and runs:

```bash
curl -fsSLO https://raw.githubusercontent.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/main/deploy/gcp/setup.sh
bash setup.sh
```

The script fast-forwards `/opt/virtutrade` to `main`, reinstalls the package,
keeps the database and `/etc/virtutrade/virtutrade.env`, records `GIT_COMMIT`
and restarts the services. After each deploy, `/health` must return 200 with the
new `commit`.

**Rolling back.** If a release breaks something, run `git revert <merge commit>`
on a new branch, open a pull request and merge it; CI and the normal deploy put
the last good version back, and the history shows what was undone. When the site
is down and cannot wait for CI, put the previous good tag back on the VM
directly:

```bash
sudo git -C /opt/virtutrade checkout --quiet v1.0
sudo sed -i "s/^GIT_COMMIT=.*/GIT_COMMIT=$(sudo git -C /opt/virtutrade rev-parse HEAD)/" /etc/virtutrade/virtutrade.env
sudo systemctl restart virtutrade-web virtutrade-feed
```

Then follow up with the revert. The next `bash setup.sh` returns the VM to
`main`, so `main` and the URL match again.

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
Latest green run on `main`: [run 43745601494](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/actions/runs/43745601494)
(commit `4d65bd1`, 16 November 2026, the first commit deployed to the VM).

**Branch protection.** The [`main-protection` ruleset](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/rules/21540407)
is active on the default branch with no bypass list. It requires a pull request
with one approving review, and blocks force pushes and deletion of `main`. It
does not yet require a green status check; team members cannot change rulesets,
so the request is with the repository admin (section 4).

## 3. Monitoring

**What is logged.** gunicorn writes one access line per request (time, method,
path, status, size) to standard output. The app logs a warning when the market
feed loses its connection, when `/health` fails (exception type only), and when
market data cannot be read. systemd's journal keeps the logs on the VM; read
them over SSH with `journalctl -u virtutrade-web -u virtutrade-feed -f`.

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
| Response time | Request duration in the access log (gunicorn `%(L)s` field) | Pages slower than 2 s |

UptimeRobot (free plan) calls `/health` every 5 minutes and e-mails the PO when
it does not return 200; three more monitors watch `/`, `/login` and `/register`.
Set up on 16 November 2026; all four were up at 100% on the first day.

## 4. Known risks and technical debt

| Item | Layer | What could happen | Plan |
|---|---|---|---|
| The database lives on one VM | infrastructure | A disk failure, or deleting the VM, loses accounts and trades | Accepted for a class demo: the test accounts can be re-seeded, and the SQLite file is copied off the VM weekly (section 5) |
| Charges outside the free tier | infrastructure | The billing account has no free-trial credit, so a second VM, a larger or SSD disk, snapshots or a reserved IP would be charged to the card; the external IPv4 address may be charged too | Stay at one `e2-micro` with a 30 GB standard disk and no snapshots; a budget alert e-mails the PO; check Billing → Reports weekly; delete the VM once the course is graded |
| Shared public test accounts | data | Anyone can trade on them or lock one with five wrong passwords | Accepted: virtual money only, three accounts, a lock lasts 15 minutes and anyone can register |
| Confirm needs the exact previewed quote time | code | With moving prices, "Price changed" makes users preview again | Accepted for v1.0: it stops orders at a price the user did not see; the simulator moves every 20 s |
| Real prices depend on DNSE access | infrastructure | The API key returned 401 on 7 November, and the public chart endpoint is unofficial | Accepted: the hosted app uses the labelled simulator; real data stays documented in `docs/DNSE.md` |
| Browser behaviour is not checked in CI | tests | A chart or watchlist regression passes CI | Playwright scripts in `scripts/` are run before each release; #148 adds an accessibility check |
| A red pull request can still be merged | infrastructure | The ruleset does not yet require a green status check | Reviewers approve only after CI is green; the repository admin is asked to add **Python tests** as a required check |

## 5. Maintenance plan

Owners are proposed by the PO and confirmed at Sprint 5 planning.

| Area | What to do | Owner | How often |
|---|---|---|---|
| Bugs | Triage new `bug` issues, reproduce with a failing test, fix through a reviewed PR | Thanh (triage), area owner (fix) | Weekly, same day for P0 |
| Dependency updates | Check `requirements.txt`, the `dev` extra and the vendored chart library; update one at a time with CI green | Tue | Monthly |
| Backups of the data | Copy `/var/lib/virtutrade/simulation.db` off the VM (stop `virtutrade-feed`, `sudo cp`, start it, download over SSH) | Long | Weekly and before every release |
| Monitoring | Read the `/health` monitor e-mails, the 5xx count and the latest CI run on `main` | Vu | Daily in demo week, otherwise weekly |
| Keeping the docs true | Update README, `docs/testing.md` and this file in the same PR as the change (Definition of Done) | Each PR author; Scrum Master checks | Every PR; checked at sprint review |

## 6. Lessons learned

| What happened | What we changed | What we would do differently |
|---|---|---|
| Test evidence drifted from `main`: the M4 dossier listed tests as "Branch" long after they merged, and the final reconciliation (#139) landed hours before the deadline | A checker script (#134) resolves every test named in `docs/testing.md`, and CI runs its test | Update the dossier in the same PR as the test, not at the end |
| Long-lived branches conflicted: the Portfolio PR (#103) sat in conflict and the sell tests (#133) needed several re-reviews | Smaller PRs, an agreed merge order, and rebasing as soon as `main` moves | Open a draft PR on day two of a sprint and merge in small steps every day |
| An outside dependency failed silently: the DNSE key stopped working and we only noticed while building charts | `/health`, a labelled practice simulator, and a credential-free fallback for real data | Check third-party credentials on a schedule from the first day they are used |

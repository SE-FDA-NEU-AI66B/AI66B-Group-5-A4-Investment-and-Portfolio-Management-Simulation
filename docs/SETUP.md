# Run VirtuTrade on a new machine

## Prerequisites

- Git 2.30+ (`git --version`).
- Python 3.10+ with pip and venv (locally checked on 3.10.11; CI uses 3.12).
- Browser and Internet for cloning/installing packages.
- No Node, Docker, database server or DNSE credentials needed for this slice.

## Windows PowerShell

First check which launcher you have: run `py -3 --version`. If it errors with
"py is not recognized", replace `py -3` with `python` everywhere in the block
below and confirm `python --version` reports 3.10 or newer.

```powershell
git clone https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation.git
cd AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation
py -3 -m venv .venv
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m virtutrade init-db
.\.venv\Scripts\python.exe -m virtutrade run
```

Using the venv Python directly avoids activation-policy problems. Both `py -3`
and `python` are only needed to create the virtual environment; every command
after that uses the venv's own Python by full path.

## macOS / Linux

```bash
git clone https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation.git
cd AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation
python3 -m venv .venv
cp .env.example .env
.venv/bin/python -m pip install -e .
.venv/bin/python -m virtutrade init-db
.venv/bin/python -m virtutrade run
```

## Configuration and database

| Variable | Default | Meaning |
|----------|---------|---------|
| DATABASE_PATH | `instance/virtutrade.db` | Relative paths resolve from the repository, not the shell's current directory |
| HOST | `127.0.0.1` | Local development interface |
| PORT | `5000` | Change to 5001 if occupied |

Defaults work unchanged. Environment variables override `.env`. Never commit
credentials, `.env` or database files; `.gitignore` excludes local state.
One command, `python -m virtutrade init-db`, creates six tables and seeds **12 instruments and
12 price_quote rows**. It prints `Database ready: 12 price_quote rows (12 on a
fresh database).` The four other tables stay empty. Re-running preserves current
prices and inserts missing demo entries; it does not reset data. Account and quote migrations are applied idempotently.

Schema upgrades (proposed contract in `docs/account-migration.md`, implemented
under #77): copy the database file first and migrate the copy, never a live
database — verify row counts and ids before swapping the file back. Reruns of a
guarded migration are no-ops. If a migration fails midway, delete the broken
copy and start again from the untouched original; the applier rolls back
partial work.

Page-specific code is grouped under `src/virtutrade/market/`; schema and initialization
are under `src/virtutrade/database/`. See [code structure](code-structure.md) for the
file to open when debugging a route, calculation, query, template or stylesheet.
The editable install registers this checkout as a Python package and reads
the pinned runtime dependency from requirements.txt via pyproject.toml. Keep
the checkout in place: .env and data/demo-quotes.json resolve from its root.
The previous root app.py command is replaced by python -m virtutrade; after
updating an old checkout, rerun the install command in its virtual environment.

## How to know it worked

Open **http://127.0.0.1:5000/market**. The page says “Market snapshot” and “12
symbols · VND”; HPG is 28,000 VND and FPT is 120,000 VND on a fresh seed. Rows
show Demo / seed, UTC timestamps and warnings after 15 minutes. These fixed
prices are not live DNSE data. Restarting preserves the DB; Ctrl+C stops the app.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| No module named virtutrade | From the cloned repo root, rerun the venv Python with `-m pip install -e .`; run the app using that same Python. |
| No module named flask/dotenv | Run pip and app with the same venv Python shown above; reinstall requirements. |
| Address/port already in use | Set PORT=5001 in `.env`, restart and open http://127.0.0.1:5001/market. |
| Market data is unavailable (503) | Check DATABASE_PATH/permissions, then run init-db with the server's environment; inspect terminal logs for the actual DB error. |
| Linux cannot create venv | Install the OS's matching venv support (Debian/Ubuntu: python3-venv), then repeat creation. |
| No quotes yet | DB exists but has no quotes; run init-db and reload. |
| `UnicodeEncodeError: 'charmap' codec can't encode character` during `pip install -e .` (Windows) | The checkout path contains non-ASCII characters (e.g. `D:\Học tập\...`); Python 3.11 on Windows writes the editable-install `.pth` file in cp1252. Clone into an ASCII-only path such as `D:\code\`. Alternatively run `setx PYTHONUTF8 1`, open a new terminal and reinstall; the variable must stay set whenever the venv is used. |

## Tests

`pytest` is a development-only dependency and is deliberately not in
`requirements.txt`. Install it with the same venv Python, then run the suite
from the repository root.

PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\pytest.exe -v
```

To use the instructor's literal `pytest` command in PowerShell, activate the
environment first with `.\.venv\Scripts\Activate.ps1`, then type `pytest`.
If PowerShell blocks activation, the `pytest.exe -v` command above runs the
same suite without changing the machine's execution policy.

macOS / Linux:

```bash
.venv/bin/python -m pip install pytest
.venv/bin/pytest -v
```

GitHub Codespaces: the repository's [devcontainer](../.devcontainer/devcontainer.json)
creates `.venv`, installs the checkout plus `pytest`, copies `.env` and runs
`init-db` when the codespace is created, and puts `.venv/bin` first on PATH, so
plain `pytest -v` works in a new terminal. A codespace created before this file
existed must be rebuilt once (Command Palette → **Codespaces: Rebuild
Container**). Without a rebuild, bare `pytest` is the image's global pipx copy
and every test module fails to collect with `ModuleNotFoundError: No module
named 'virtutrade'`; use `.venv/bin/python -m pip install pytest` and
`.venv/bin/pytest -v` instead.

Alternatively, run `source .venv/bin/activate` and then `pytest`. Tests use
temporary SQLite files and do not require a running server, real credentials,
or the app's persistent database. Capture the full `python -m pytest -v`
output for the Milestone 4 submission after all reviewed tests have merged.

Run the full suite; auth and buy tests use real temporary SQLite databases and do not change the
running demo's data. CI installs `pytest`, `pytest-cov` and `ruff` separately
and runs on Python 3.12.

For the final Milestone 4 screenshot on a fresh clone, install this checkout in
its new venv as above, then run the **unmodified** suite with the venv on PATH:

```powershell
$env:PATH = (Resolve-Path .\.venv\Scripts).Path + ';' + $env:PATH
pytest -v
```

On macOS/Linux, use `.venv/bin/pytest -v`. Capture the complete test-name and
summary output with the checked-out commit SHA after the P0 test PRs have
merged. Do not set `PYTHONPATH` to another checkout or substitute selected
tests for the full run. Long's independent-machine result for #123 is recorded
under [Independent verification](#independent-verification) below. An author
run is not that evidence.

## Independent verification

A non-author must follow these updated module-install/run commands on a
different machine from a clean clone and record the exact tested commit.
Earlier runs using root app.py do not verify this src-layout revision.
The run below was recorded for Milestone 4 under #123.

| Field | Value |
|-------|-------|
| Tested by | Bùi Khang Long (`longbk761-bot`) |
| Date | 2 November 2026, 20:53–21:14 UTC+7 |
| OS | Microsoft Windows 11 Pro 10.0.26200 (Build 26200) |
| Python | 3.11.9 |
| Git | 2.53.0.windows.2 |
| Commit SHA | `fc47196da39c3019ff67a68c9047ef21db223361` (`main` after PR #140) |
| Elapsed (clone to page loaded) | 4 minutes (20:53:58 to 20:57:45 UTC+7) |
| Tests | `python -m pytest -v` from the repository root in the activated venv: 314 collected |
| Result | **312 passed, 2 skipped in 52.53 s**; `/market` showed "Market snapshot", "12 symbols · VND", HPG 28,000 and FPT 120,000 (Demo / seed) |
| Notes | Fresh folder `D:\m4-check`; commands run in Git Bash (MINGW64) as the equivalent of the PowerShell block above, using `.venv/Scripts/python.exe`. `.env` was copied from `.env.example` with no edits; no real credentials or database dump were used. After the run `git status` showed a clean tree except the untracked `pytest-v.txt` output file. The board URL in README opened. Open PRs #133, #134 and #139 were not yet merged at this SHA. |

Evidence: [market page](images/m4/clean-clone-2026-11-02/market-page.png);
`date` at [clone start](images/m4/clean-clone-2026-11-02/date-start.png) and
[page loaded](images/m4/clean-clone-2026-11-02/date-page-loaded.png);
`python -m pytest -v` with every test name in six overlapping screenshots:
[1](images/m4/clean-clone-2026-11-02/pytest-v-1.png),
[2](images/m4/clean-clone-2026-11-02/pytest-v-2.png),
[3](images/m4/clean-clone-2026-11-02/pytest-v-3.png),
[4](images/m4/clean-clone-2026-11-02/pytest-v-4.png),
[5](images/m4/clean-clone-2026-11-02/pytest-v-5.png),
[6](images/m4/clean-clone-2026-11-02/pytest-v-6.png).

**Reproducible failure found during #123:** the tester's usual checkout under
`D:\Học tập\...` failed at `pip install -e .` with `UnicodeEncodeError`
(Windows, Python 3.11, cp1252). The clean clone above used an ASCII-only path and
passed, including `tests/test_cli.py`, which requires the installed package.
The workaround is now listed under Troubleshooting.

**PO local clean-clone check, 3 October:** Windows/Python 3.10.11, main commit
`b5fdb0f`; fresh venv and database, repeated init-db, tests and lint passed.
See [handoff evidence](m2-po-handoff.md). A local author check does not satisfy
the independent-machine condition above.


## Local simulation and authenticated buy (PR #92)

Set `QUOTE_MODE=simulation` and `DATABASE_PATH=instance/simulation.db` in the
ignored local `.env`, choosing a NEW database path. Then run:

```powershell
.\.venv\Scripts\python.exe -m virtutrade init-demo
.\.venv\Scripts\python.exe -m virtutrade run
```

On macOS/Linux use `.venv/bin/python` for the same commands. `init-demo` refuses
existing files; to continue an existing simulation, run the server and use
Generate demo quotes. Do not delete a database that holds work you need.
Open http://127.0.0.1:5000/ and click Register. For a disposable classroom account
use `learner@example.test` with a password of your own choice (8–128 characters);
no preset password or real account is required. The initial grant is 100,000,000 VND.

Click Buy shares, enter HPG and 1000 shares, and preview 28,000,000 VND. If stale,
click Generate demo quotes and preview again. Confirm once: cash becomes
72,000,000 VND and the receipt shows 1,000 shares with a 28,000,000 VND cost basis.
For the initial balance, 4,000 HPG shows a 12,000,000 VND shortfall and disables
confirmation. All quotes are labelled Simulation / generated, never live DNSE.
Logout/Login are visible from Market; the grant is not repeated on login.

The real Portfolio screen and Sell are still separate #81/#79 deliveries. The
buy receipt is not a portfolio substitute. A missing /portfolio link means that
module has not landed; never type a missing URL as an acceptance workaround.
If an order result is unknown, do not resubmit: reconcile the database with the
operator (or Portfolio when available). No automatic order retry is performed.

`SECRET_KEY` may be empty for local use: a fresh signing key is generated each
boot. For stable CSRF across restarts generate a private value locally and put
it only in `.env`: `python -c "import secrets; print(secrets.token_hex(32))"`.
Registration/login still require same-origin requests and CSRF tokens.

Optional author browser smoke: install `playwright==1.63.0` in the dev venv and
run `python scripts/check_buy_ui.py` on Windows with Microsoft Edge installed.
It uses a temporary DB/server and real registration/login with a random disposable
password; it does not replace the independent-machine verification under #83.

## Optional DNSE market data — #59

PR #60's WebSocket worker is merged. Follow [DNSE.md](DNSE.md), set
`QUOTE_MODE=dnse`, use a separate `DATABASE_PATH=instance/dnse.db`, and keep keys
in the ignored `.env`. Leave `DNSE_SYMBOLS` empty for all known instruments.
Run `python -m virtutrade init-db`, then `python -m virtutrade stream`;
run `python -m virtutrade run` in another terminal with the same configuration.
The stream worker also fetches latest matched prices at startup and every
60 seconds, so an evening startup does not require waiting for tomorrow's tick.
The website preserves actual trade timestamps and excludes demo prices in DNSE mode.
The labelled simulation workflow above needs no provider keys.
The PO confirmed the three-symbol provider-board comparison on 20 October;
independent follow-up review and merge remain pending.
Repeat independent-machine SETUP on the final merged revision under #83.

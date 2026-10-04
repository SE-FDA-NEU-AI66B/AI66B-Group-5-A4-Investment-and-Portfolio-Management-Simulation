# Run VirtuTrade on a new machine

## Prerequisites

- Git 2.30+ (`git --version`).
- Python 3.10+ with pip and venv (locally checked on 3.10.11; CI uses 3.12).
- Browser and Internet for cloning/installing packages.
- No Node, Docker, database server or DNSE credentials needed for this slice.

## Windows PowerShell

```powershell
git clone https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation.git
cd AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation
py -3 -m venv .venv
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py init-db
.\.venv\Scripts\python.exe app.py
```

Using the venv Python directly avoids activation-policy problems. If `py` is
unavailable but `python --version` is 3.10+, use `python -m venv .venv`.

## macOS / Linux

```bash
git clone https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation.git
cd AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation
python3 -m venv .venv
cp .env.example .env
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py init-db
.venv/bin/python app.py
```

## Configuration and database

| Variable | Default | Meaning |
|----------|---------|---------|
| DATABASE_PATH | `instance/virtutrade.db` | Relative paths resolve from the repository, not the shell's current directory |
| HOST | `127.0.0.1` | Local development interface |
| PORT | `5000` | Change to 5001 if occupied |

Defaults work unchanged. Environment variables override `.env`. Never commit
credentials, `.env` or database files; `.gitignore` excludes local state.
One command, `app.py init-db`, creates six tables and seeds **12 instruments and
12 price_quote rows**. It prints `Database ready: 12 price_quote rows (12 on a
fresh database).` The four other tables stay empty. Re-running preserves current
prices and inserts missing demo entries; it does not reset data or migrate schemas.

Page-specific code is grouped under `virtutrade/market/`; schema and initialization
are under `virtutrade/database/`. See [code structure](code-structure.md) for the
file to open when debugging a route, calculation, query, template or stylesheet.
This packaging does not change the commands above.

## How to know it worked

Open **http://127.0.0.1:5000/market**. The page says “Market snapshot” and “12
symbols · VND”; HPG is 28,000 VND and FPT is 120,000 VND on a fresh seed. Rows
show Demo / seed, UTC timestamps and warnings after 15 minutes. These fixed
prices are not live DNSE data. Restarting preserves the DB; Ctrl+C stops the app.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| No module named flask/dotenv | Run pip and app with the same venv Python shown above; reinstall requirements. |
| Address/port already in use | Set PORT=5001 in `.env`, restart and open http://127.0.0.1:5001/market. |
| Market data is unavailable (503) | Check DATABASE_PATH/permissions, then run init-db with the server's environment; inspect terminal logs for the actual DB error. |
| Linux cannot create venv | Install the OS's matching venv support (Debian/Ubuntu: python3-venv), then repeat creation. |
| No quotes yet | DB exists but has no quotes; run init-db and reload. |

## Tests

`pytest` is a development-only dependency and is deliberately not in
`requirements.txt`. Install it with the same venv Python, then run the suite
from the repository root.

PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe -m pytest -q
```

macOS / Linux:

```bash
.venv/bin/python -m pip install pytest
.venv/bin/python -m pytest -q
```

Expected: `34 passed`. Tests use temporary databases and do not change the
running demo's data. CI installs `pytest`, `pytest-cov` and `ruff` separately
and runs on Python 3.12.

## Independent verification

A non-author following this guide on a different machine from a clean clone.

| Field | Value |
|-------|-------|
| Tested by | TESTER_NAME |
| Date | TESTER_DATE |
| OS | TESTER_OS |
| Python | TESTER_PY |
| Git | TESTER_GIT |
| Commit SHA | TESTER_SHA |
| Elapsed (clone to page loaded) | TESTER_MIN minutes |
| Tests | TESTER_TESTS |
| Result | TESTER_RESULT |
| Notes | TESTER_NOTES |

**PO local clean-clone check, 3 October:** Windows/Python 3.10.11, main commit
`b5fdb0f`; fresh venv and database, repeated init-db, tests and lint passed.
See [handoff evidence](m2-po-handoff.md). A local author check does not satisfy
the independent-machine condition above.

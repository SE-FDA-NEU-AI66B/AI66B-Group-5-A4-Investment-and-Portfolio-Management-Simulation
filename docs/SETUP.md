# Run VirtuTrade on a new machine

This guide takes a clean clone to a working P0 story in about 15 minutes. It
needs **no DNSE keys** and no real money: the classroom demo runs on labelled
simulation quotes in a local SQLite file.

## Prerequisites

- Git 2.30+ (`git --version`).
- Python 3.10+ with pip and venv (CI uses 3.12).
- A browser, plus Internet for cloning and installing packages.
- No Node, Docker, database server or DNSE credentials.
- **Windows:** clone into a folder whose path has only ASCII letters, for
  example `C:\code` or `D:\code`. With Vietnamese characters in the path (for
  example `D:\Học tập\...`), `pip install -e .` fails with `UnicodeEncodeError`.

## 1. Install

### Windows (PowerShell or Git Bash)

First check your launcher: `py -3 --version`. If you get "py is not recognized",
use `python` instead of `py -3` below and check that `python --version` is 3.10 or newer.

```powershell
git clone https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation.git
cd AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
Copy-Item .env.example .env
```

In Git Bash, write the paths with `/` (`.venv/Scripts/python`) and use `cp` instead of `Copy-Item`.
Calling the venv's Python by its full path avoids activation-policy problems.

### macOS / Linux

```bash
git clone https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation.git
cd AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation
python3 -m venv .venv
.venv/bin/python -m pip install -e .
cp .env.example .env
```

`pip install -e .` installs this checkout plus the runtime dependencies pinned
in `requirements.txt`: **Flask 3.1.3** (with python-dotenv) and **websockets
15.0.1**. websockets is used only by the optional DNSE worker. Keep the checkout
in place, because `.env` and `data/` resolve from its root. After pulling new
commits, rerun the same install command so new dependencies arrive.

## 2. Configure the classroom demo (simulation, no keys)

Edit the ignored `.env` and set these two lines. Leave the rest as they are.

```
DATABASE_PATH=instance/simulation.db
QUOTE_MODE=simulation
```

| Variable | Default in `.env.example` | Meaning |
|----------|---------------------------|---------|
| DATABASE_PATH | `instance/virtutrade.db` | SQLite file. Relative paths resolve from the repository root. Use a **new** file for simulation. |
| HOST / PORT | `127.0.0.1` / `5000` | Local interface and port. Set `PORT=5001` if 5000 is busy. |
| QUOTE_MODE | `seed` | `simulation` enables generated, labelled demo quotes and the **Generate demo quotes** button. `seed` shows fixed example prices that go stale after 15 minutes and cannot be traded. |
| SECRET_KEY | empty | Signs sessions and CSRF tokens. Leaving it empty is fine locally: a random key is generated on each start, so you must log in again after a restart. Generate a private value with `python -c "import secrets; print(secrets.token_hex(32))"`. Never commit it. |
| DNSE_API_KEY / DNSE_API_SECRET / DNSE_SYMBOLS | empty / empty / `HPG,FPT` | Only for the optional live worker (see [DNSE.md](DNSE.md)). The demo does not need them. |

Environment variables override `.env`. Never commit `.env` or database files;
`.gitignore` excludes them.

## 3. Create the database and start

```powershell
.\.venv\Scripts\python.exe -m virtutrade init-demo
.\.venv\Scripts\python.exe -m virtutrade run
```

`init-demo` creates the tables and seeds 12 instruments with generated quotes.
It prints `Simulation database ready: 12 generated quotes; open Market and
Register to start.` It refuses to overwrite an existing file, so your trades
are never reset by accident. `init-demo` and `init-db` apply the schema
migrations idempotently. To upgrade a database you need to keep, copy the file
first and run `init-db` on the copy (see [account-migration.md](account-migration.md)).
Ctrl+C stops the server, and restarting keeps the data.

`init-db` (seed mode) still exists for the read-only market snapshot: with the
default `.env` it creates `instance/virtutrade.db` with 12 fixed example prices.

## 4. Complete a P0 story and a rejection (about 3 minutes)

Open **http://127.0.0.1:5000/**. It redirects to **Market**, where the rows are labelled
*Simulation / generated*.

1. **Register (US01, US02).** Click **Register**. Use the disposable classroom
   account `learner@example.test` and a password you choose (8–128 characters).
   There is no preset password. The header shows your email; the balance is
   **100,000,000 VND**.
2. **Buy (US04).** Click **Buy shares**, then **Generate demo quotes**. Choose
   **HPG**, enter **1000**, and click **Preview order**. Check the price and total,
   then click **Confirm buy**. The receipt shows the shares bought and the cash
   remaining.
3. **Rejection (US10 / BR1).** Enter a quantity that costs more than your cash,
   for example **5000** HPG. The page shows **"Exceeds available balance by …
   VND. Reduce the quantity."** and **Confirm buy** stays disabled. Entering
   **0** shows **"Quantity must be a whole number of at least 1 share."**
4. **Sell (US05).** Click **Sell shares**, choose HPG and enter more than you hold
   (for example 1500). The page shows **"You hold 1,000 HPG; the maximum you can
   sell is 1,000."** Then sell 400 and confirm.
5. **Portfolio (US06), once #81 is merged.** Click **Portfolio**. It shows
   holdings, average cost, unrealised P&L and the total (cash + holdings).
   Logging out and back in lands on your Portfolio, and the grant is not repeated.

If a preview says *"Price may be delayed. Generate demo quotes, then preview
again."*, click **Generate demo quotes** and preview again. If an order result is
unknown (connection lost), do not resubmit. Check Portfolio first. No order is
ever retried automatically and nothing is sent to a broker.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `UnicodeEncodeError` during `pip install -e .` on Windows | The repository path contains non-ASCII characters. Clone into an ASCII-only folder such as `D:\code` and install again. |
| No module named virtutrade / flask / websockets | Run pip and the app with the same venv Python: `…\.venv\Scripts\python.exe -m pip install -e .` from the repository root. |
| `Set QUOTE_MODE=simulation and a new DATABASE_PATH first.` | `init-demo` only runs in simulation mode. Edit `.env` as in step 2. |
| `Database already exists; use Generate demo quotes instead of resetting it.` | The simulation file exists. Just run the server, or point `DATABASE_PATH` at a new file for a fresh start. |
| Preview fails with *"Price may be delayed. Wait for a fresh market quote…"* (HTTP 409) and there is no Generate button | You are in seed mode (rows say *Demo / seed*). Switch `.env` to simulation (step 2), run `init-demo`, and restart. |
| Logged out after restarting the server | `SECRET_KEY` is empty, so a new key was generated. Log in again, or set a private `SECRET_KEY` in `.env`. |
| `Account locked. Try again in 900 seconds.` | Five wrong passwords in a row lock the account for 15 minutes. Wait, or register another disposable `@example.test` account. |
| Address/port already in use | Set `PORT=5001` in `.env`, restart and open http://127.0.0.1:5001/. |
| Market data is unavailable (503) | Check `DATABASE_PATH` and permissions, run `init-demo` (or `init-db`) with the same `.env`, and read the server log. |
| Linux cannot create venv | Install the OS's venv package (Debian/Ubuntu: `python3-venv`), then repeat. |

## Tests

Development tools are not in `requirements.txt`. Install them into the same venv:

```powershell
.\.venv\Scripts\python.exe -m pip install pytest ruff
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

Every test builds its own temporary SQLite database, so the suite never changes
your demo data. CI installs `pytest`, `pytest-cov` and `ruff` and runs on Python 3.12.

Optional browser checks (authors' QA, not a substitute for the verification
below): install `playwright==1.63.0`, then run `scripts/check_buy_ui.py`,
`scripts/check_sell_ui.py`, `scripts/check_quote_change_ui.py`, or the full P0 audit
`scripts/check_p0_journeys.py` (#82). They use Microsoft Edge by default.

## Independent verification (M3, #83)

A tester who did **not** write the feature under test follows sections 1–4 from a
clean clone on their own machine. The tester records their own run below.
Never copy values from another person's run, and M2 evidence does not count for M3.
If startup or schema changes after the run, repeat it on the final merged commit.

To fill the environment rows accurately, run this in the clone after step 1:

```powershell
.\.venv\Scripts\python.exe scripts/setup_record.py
```

| Field | Value |
|-------|-------|
| Tested by | pending |
| Date | pending |
| Start → end (clone → story done) | pending |
| OS | pending |
| Python | pending |
| Git | pending |
| Tested commit | pending |
| P0 story completed via UI | pending |
| Rejection observed via UI | pending |
| Tests | pending |
| Evidence | pending |
| Notes / problems met | pending |

M2 record, kept for history only: on 3 October the PO did a local clean-clone check on
Windows/Python 3.10.11 at commit `b5fdb0f` ([handoff](m2-po-handoff.md)). It was
an author check and predates M3.
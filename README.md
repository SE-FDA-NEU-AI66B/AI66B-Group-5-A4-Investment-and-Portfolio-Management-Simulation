# AI66B - Group 5 - Topic A4: Investment & Portfolio Management Simulation (Paper Trading)


## Sprint 3 / Milestone 3: start here

**Product Owner:** @bianh13 · **Scrum Master:** @longbk761-bot (Long).
M3 opens **9 October 2026, 00:00** and is due **21 October 2026, 00:00 (UTC+7)**;
submit before the end of 20 October. [Issues](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/milestone/2)
· [Sprint plan](docs/sprint-log.md#sprint-3---milestone-3)
· [UI dossier](docs/ui.md) · [SETUP](docs/SETUP.md).

Current implementation baseline: only the public database-backed market snapshot
runs. The entry points below are the M3 navigation plan, **not a claim that the
unbuilt screens work**. Start the app using SETUP and open its documented home URL;
all P0 journeys must eventually be reachable by visible links/buttons.

| P0 story | Where the user starts | Current status |
|----------|-----------------------|----------------|
| US01 — Register / sign in | Landing page → Register / Sign in | not started |
| US02 — Initial virtual capital | Register → portfolio balance | not started |
| US03 — Find a stock and inspect its quote | Market → search → stock detail | partly works |
| US04 — Buy shares | Market detail → Buy | not started |
| US05 — Sell shares | Portfolio holding → Sell | not started |
| US06 — View portfolio | Navigation → Portfolio | not started |
| US10 — Insufficient-balance warning | Buy form → change quantity → preview | not started |

No login or seeded test account exists on the current baseline. Fake local test
accounts and their setup instructions must be added with authentication; never
put real credentials in README or SETUP. Live DNSE data (#59) is P1; the instructor's
P0 demonstration must also work with clearly labelled simulation data in the DB.


## Introduction

A **"paper trading"** application: Users can buy and sell stocks using **virtual money** based on real-world reference prices. The system automatically tracks the profit and loss (PnL) of each investment portfolio.

**Sprint 2 / Milestone 2:** [Assigned issues](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/milestone/1) · [Sprint plan](docs/sprint-log.md#sprint-2---milestone-2). Submission deadline: **5 October 2026, 00:00 (UTC+7)**.

**Run the M2 walking skeleton:** [New-machine setup guide](docs/SETUP.md). `/market` reads 12 demo quotes from SQLite; the optional [DNSE worker](docs/DNSE.md) is under Sprint 3 verification and trading remains backlog work. [Design draft](docs/design.md) · [API contract](docs/api-contract.md).

**Code modules:** The market page's routes, service, query, HTML and CSS live in
[src/virtutrade/market/](src/virtutrade/market/); shared schema/seed code lives in
[src/virtutrade/database/](src/virtutrade/database/). The application factory is
[src/virtutrade/app.py](src/virtutrade/app.py). See the
[folder map and maintenance guide](docs/code-structure.md).

```text
src/virtutrade/  Application code, grouped by business module
data/           Committed seed data
tests/          Automated checks
docs/           Design, SETUP and submission evidence
scripts/        Diagram maintenance
```

Within each feature, routes/controllers handle HTTP, services handle rules,
repositories handle SQL, and models carry data. The market service accepts a
reader interface so its rules can be tested without a server or database.

**Key Features**

* Update stock reference prices.

* Place buy/sell orders using virtual money and record transaction history.

* Calculate portfolio performance (Profit/Loss, Return on Investment, etc.).

* User leaderboard.

**Key Technical Challenge:** Ensuring absolute accuracy in financial calculations — focusing on the **Functional Suitability** characteristic according to the ISO/IEC 25010 standard.

## Team Members

| **Full Name** | **Student ID** | **GitHub Username** | **Role** | 
|----|-------|----------|--------|
| Pham Huy Thanh | 11247351 | bianh13 | Product Owner / Developer (Sprint 3) |
| Pham Quang Vu | 11247372 | VuSiSi | Dev Team |
| Nguyen Van Tue | 11247366 | nguyentue110 | Developer (Sprint 3); Scrum Master in Sprint 2 |
| Bui Khang Long | 11247312 | longbk761-bot | Scrum Master / Developer (Sprint 3) |

> *Note: The Scrum Master role rotates every sprint. Each member will take on this role at least once during the semester.*

## Unresponsive Member Policy

If a team member is unresponsive for 48 hours without prior notice, the Scrum Master will reach out to them directly. If there is no response or resolution within 3 days, the issue will be escalated to the instructor.

## Technology Stack

* **Language:** Python 3.10+

* **Backend / UI:** Flask 3.1.3 with server-rendered HTML.

* **Database:** SQLite; six tables, 12 seeded instruments and 12 quote rows for M2.

* **Version Control & CI:** Git, GitHub and GitHub Actions; Python integration tests run on PRs.

## Installation

```bash
git clone https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation.git
cd AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation
```

Then follow the OS-specific commands in [docs/SETUP.md](docs/SETUP.md) to create
the virtual environment, install dependencies, copy configuration and initialize
the database with one command. The walking skeleton is available on `main`.

## Running the Application

```bash
python -m virtutrade init-db
python -m virtutrade run
```

After installing the checkout with `python -m pip install -e .` as shown in
SETUP, run with the configured virtual environment's Python. Open
http://127.0.0.1:5000/market; expect 12 symbols with a **Demo / seed** label.

## Team Workflow

* **Backlog & Board:** [Group 5 - VirtuTrade Board](https://github.com/orgs/SE-FDA-NEU-AI66B/projects/7)

* **Product Owner:** [bianh13](https://github.com/bianh13)

* **Scrum Master for Sprint 3 (current):** [longbk761-bot](https://github.com/longbk761-bot). Previous: Sprint 1 [VuSiSi](https://github.com/VuSiSi); Sprint 2 [nguyentue110](https://github.com/nguyentue110).

* **Definition of Done:** [docs/definition-of-done.md](docs/definition-of-done.md)

* **Requirements:** [docs/requirements.md](docs/requirements.md)

* **Sprint log:** [docs/sprint-log.md](docs/sprint-log.md)

* **Traceability:** [docs/traceability.md](docs/traceability.md)

* **Process dossier:** [docs/process.md](docs/process.md)

* **UML diagrams:** [docs/diagrams](docs/diagrams)

* **Branching:** `feature/<description>` → Open a Pull Request to `main` → Requires at least 1 review/approval before merging.

* **Commit Message Convention:** `USxx: brief description` (referencing the corresponding User Story).

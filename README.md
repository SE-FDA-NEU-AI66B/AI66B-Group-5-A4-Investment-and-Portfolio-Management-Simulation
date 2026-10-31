# AI66B - Group 5 - Topic A4: Investment & Portfolio Management Simulation (Paper Trading)

## Sprint 4 / Milestone 4: current work

**Product Owner and Scrum Master:** @bianh13 (Thanh). Sprint 4 opened
**23 October 2026, 00:00** and the LMS submission is due **3 November 2026,
00:00 (UTC+7)**; submit during 2 November. [Assigned issues](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/milestone/3)
· [Sprint plan](docs/sprint-log.md#sprint-4---milestone-4)
· [SETUP](docs/SETUP.md).

The team is building executable tests and four-state UI evidence for P0 stories
US01–US06 and US10. Portfolio issue #81 was carried into this sprint; its
reviewed PR #103 merged on 27 October, and the Portfolio screen is now on
`main`. Long's #122 tests and #123 independent SETUP run remain separate
acceptance work. The merged app supports account access, stored Market data,
virtual Buy/Sell and Portfolio; feature availability does not replace the M4
test evidence.

Sprint 4 commitment is **40 points, 10 per member**. The team targets the first
reviewable PR from every member by 29 October, leaving 31 October–2 November
for integration checks and submission evidence.


## Sprint 3 / Milestone 3: historical plan

**Product Owner:** @bianh13 · **Scrum Master:** @longbk761-bot (Long).
M3 opens **9 October 2026, 00:00** and is due **21 October 2026, 00:00 (UTC+7)**;
submit before the end of 20 October. [Issues](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/milestone/2)
· [Sprint plan](docs/sprint-log.md#sprint-3---milestone-3)
· [UI dossier](docs/ui.md) · [SETUP](docs/SETUP.md).

At the historical M3 snapshot, registration/login/logout and the database-backed
market were implemented. Authenticated previews, virtual purchases and explicit
simulation quotes reached main through PR #92; later M3 work is recorded in
the table below rather than presented as the current Sprint 4 status.

| P0 story | Where the user starts | Current status |
|----------|-----------------------|----------------|
| US01 — Register / sign in | Market header → Register / Log in | partly works |
| US02 — Initial virtual capital | Register; balance presentation/portfolio integration pending | partly works |
| US03 — Find a stock and inspect its quote | Market → search → stock detail | partly works |
| US04 — Buy shares | Market → Buy shares | partly works |
| US05 — Sell shares | Portfolio holding → Sell | not started |
| US06 — View portfolio | Navigation → Portfolio | not started |
| US10 — Insufficient-balance warning | Buy form → change quantity → preview | partly works |

Register a disposable local account through the visible Register link; no shared or real credentials are committed.
Auth is on main via #93; independent M3 SETUP and final story acceptance remain pending.
Live DNSE data (#59) is P1 and is not required for the labelled simulation demo.



## Introduction

A **"paper trading"** application: Users can buy and sell stocks using **virtual money** based on real-world reference prices. The system automatically tracks the profit and loss (PnL) of each investment portfolio.

**Sprint 2 / Milestone 2:** [Assigned issues](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/milestone/1) · [Sprint plan](docs/sprint-log.md#sprint-2---milestone-2). Submission deadline: **5 October 2026, 00:00 (UTC+7)**.

**Run the M2 walking skeleton:** [New-machine setup guide](docs/SETUP.md). `/market` reads 12 demo quotes from SQLite; the optional [DNSE worker](docs/DNSE.md) is under Sprint 3 verification and buy/simulation is on main via #92; sell and portfolio remain pending. [Design draft](docs/design.md) · [API contract](docs/api-contract.md).

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

* **Scrum Master for Sprint 4 (current):** [bianh13](https://github.com/bianh13). Previous: Sprint 1 [VuSiSi](https://github.com/VuSiSi); Sprint 2 [nguyentue110](https://github.com/nguyentue110); Sprint 3 [longbk761-bot](https://github.com/longbk761-bot).

* **Definition of Done:** [docs/definition-of-done.md](docs/definition-of-done.md)

* **Requirements:** [docs/requirements.md](docs/requirements.md)

* **Sprint log:** [docs/sprint-log.md](docs/sprint-log.md)

* **Traceability:** [docs/traceability.md](docs/traceability.md)

* **Process dossier:** [docs/process.md](docs/process.md)

* **UML diagrams:** [docs/diagrams](docs/diagrams)

* **Branching:** `feature/<description>` → Open a Pull Request to `main` → Requires at least 1 review/approval before merging.

* **Commit Message Convention:** `USxx: brief description` (referencing the corresponding User Story).

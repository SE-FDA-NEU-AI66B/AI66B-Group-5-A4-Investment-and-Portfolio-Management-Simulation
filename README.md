# AI66B - Group 5 - Topic A4: Investment & Portfolio Management Simulation (Paper Trading)

## Introduction

A **"paper trading"** application: Users can buy and sell stocks using **virtual money** based on real-world reference prices. The system automatically tracks the profit and loss (PnL) of each investment portfolio.

**Sprint 2 / Milestone 2:** [Assigned issues](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/milestone/1) · [Sprint plan](docs/sprint-log.md#sprint-2---milestone-2). Submission deadline: **5 October 2026, 00:00 (UTC+7)**.

**Run the M2 walking skeleton:** [New-machine setup guide](docs/SETUP.md). `/market` reads 12 demo quotes from SQLite and refreshes automatically. An optional [DNSE worker](docs/DNSE.md) receives stock quotes using local API credentials; real-provider verification is pending. Login, trading and Admin services remain backlog work. [Design draft](docs/design.md).

**Key Features**

* Update stock reference prices.

* Place buy/sell orders using virtual money and record transaction history.

* Calculate portfolio performance (Profit/Loss, Return on Investment, etc.).

* User leaderboard.

**Key Technical Challenge:** Ensuring absolute accuracy in financial calculations — focusing on the **Functional Suitability** characteristic according to the ISO/IEC 25010 standard.

## Team Members

| **Full Name** | **Student ID** | **GitHub Username** | **Role** | 
|----|-------|----------|--------|
| Pham Huy Thanh | 11247351 | bianh13 | Product Owner / Lead Developer (Sprint 2) |
| Pham Quang Vu | 11247372 | VuSiSi | Dev Team |
| Nguyen Van Tue | 11247366 | nguyentue110 | Scrum Master (Sprint 2 - Milestone 2) |
| Bui Khang Long | 11247312 | longbk761-bot | Dev Team | 

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
python app.py init-db
python app.py
```

Run with the configured virtual environment's Python. Open
http://127.0.0.1:5000/market; expect 12 symbols with a **Demo / seed** label.

## Team Workflow

* **Backlog & Board:** [Group 5 - VirtuTrade Board](https://github.com/orgs/SE-FDA-NEU-AI66B/projects/7)

* **Product Owner:** [bianh13](https://github.com/bianh13)

* **Scrum Master for Sprint 2 (current):** [nguyentue110](https://github.com/nguyentue110). Previous Sprint 1 Scrum Master: [VuSiSi](https://github.com/VuSiSi).

* **Definition of Done:** [docs/definition-of-done.md](docs/definition-of-done.md)

* **Requirements:** [docs/requirements.md](docs/requirements.md)

* **Sprint log:** [docs/sprint-log.md](docs/sprint-log.md)

* **Traceability:** [docs/traceability.md](docs/traceability.md)

* **Process dossier:** [docs/process.md](docs/process.md)

* **UML diagrams:** [docs/diagrams](docs/diagrams)

* **Branching:** `feature/<description>` → Open a Pull Request to `main` → Requires at least 1 review/approval before merging.

* **Commit Message Convention:** `USxx: brief description` (referencing the corresponding User Story).

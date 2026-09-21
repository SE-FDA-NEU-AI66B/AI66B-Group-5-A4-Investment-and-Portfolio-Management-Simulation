# AI66B - Group 5 - Topic A4: Investment & Portfolio Management Simulation (Paper Trading)

## Introduction

A **"paper trading"** application: Users can buy and sell stocks using **virtual money** based on real-world reference prices. The system automatically tracks the profit and loss (PnL) of each investment portfolio.

**Key Features**

* Update stock reference prices.

* Place buy/sell orders using virtual money and record transaction history.

* Calculate portfolio performance (Profit/Loss, Return on Investment, etc.).

* User leaderboard.

**Key Technical Challenge:** Ensuring absolute accuracy in financial calculations — focusing on the **Functional Suitability** characteristic according to the ISO/IEC 25010 standard.

## Team Members

| **Full Name** | **Student ID** | **GitHub Username** | **Role** | 
|----|-------|----------|--------|
| Pham Huy Thanh | 11247351 | bianh13 | Product Owner | 
| Pham Quang Vu | 11247372 | VuSiSi | Scrum Master (Current Sprint) | 
| Nguyen Van Tue | 11247366 | nguyentue110 | Dev Team | 
| Bui Khang Long | 11247312 | longbk761-bot | Dev Team | 

> *Note: The Scrum Master role rotates every sprint. Each member will take on this role at least once during the semester.*

## Unresponsive Member Policy

If a team member is unresponsive for 48 hours without prior notice, the Scrum Master will reach out to them directly. If there is no response or resolution within 3 days, the issue will be escalated to the instructor.

## Technology Stack

* **Language:** Python 3.10+

* **Backend / UI:** Python application; implementation details are documented in the source tree.

* **Database:** No persistent database is required for the Sprint 1 specification.

* **Version Control & CI:** Git & GitHub · CI pipeline will be set up using GitHub Actions (from Sprint 5).

## Installation

```
git clone https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation.git
cd AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation

python -m venv venv
source venv/bin/activate      # For Windows: venv\Scripts\activate
pip install -r requirements.txt   # Dependencies will be added here

```

## Running the Application

```
python app.py

```

## Team Workflow

* **Backlog & Board:** [Project Board](https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation/projects)

* **Product Owner:** [bianh13](https://github.com/bianh13)

* **Scrum Master for Sprint 1:** [VuSiSi](https://github.com/VuSiSi)

* **Definition of Done:** [docs/definition-of-done.md](docs/definition-of-done.md)

* **Requirements:** [docs/requirements.md](docs/requirements.md)

* **Sprint log:** [docs/sprint-log.md](docs/sprint-log.md)

* **Traceability:** [docs/traceability.md](docs/traceability.md)

* **Process dossier:** [docs/process.md](docs/process.md)

* **Branching:** `feature/<description>` → Open a Pull Request to `main` → Requires at least 1 review/approval before merging.

* **Commit Message Convention:** `USxx: brief description` (referencing the corresponding User Story).

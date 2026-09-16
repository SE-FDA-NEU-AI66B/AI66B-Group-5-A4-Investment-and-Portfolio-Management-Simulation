# 📈 AI66B – Group 5 – Topic A4: Investment & Portfolio Management Simulation (Paper Trading)

## Introduction

The application provides a **paper trading** environment where users can buy and sell stocks using **virtual money** based on reference prices. The system automatically tracks the profit and loss (P&L) of each investment portfolio.

**Main Features**

* Update reference stock prices
* Place virtual buy/sell orders and record transaction history
* Calculate portfolio performance (profit/loss, rate of return, etc.)
* Leaderboard comparing performance among users

**Key Technical Challenge:** ensuring accuracy in financial calculations — a key aspect of **Functional Suitability** according to the ISO/IEC 25010 standard.

## Team Members

| Full Name        | Student ID       | GitHub Username  | Role                                                        |
| ---------------- | ---------------- | ---------------- | ----------------------------------------------------------- |
| *Phạm Huy Thành* | *11247351* | *bianh13* | Product Owner                                               |
| *Phạm Quang Vũ* | *[TO BE FILLED]* | *[TO BE FILLED]* | Scrum Master (current sprint)                               |
| *Nguyễn Văn Tuệ* | *[TO BE FILLED]* | *[TO BE FILLED]* | Dev Team                                                    |
| *Bùi Khang Long* | *[TO BE FILLED]* | *[TO BE FILLED]* | Dev Team                                                    |

> The Scrum Master role rotates each sprint — every member is expected to take on the role at least once during the semester.

## Procedure for Handling an Unresponsive Team Member

*[TO BE FILLED — this section must be finalized during Sprint 0. The procedure should clearly specify: how many days of inactivity will trigger direct contact from the remaining members, who is responsible for monitoring daily check-ins, and when the issue should be reported to the instructor.]*

## Planned Technologies

* **Programming Language:** Python 3.10+
* **Backend / Interface:** *FastAPI*
* **Database:** *PostgresSQL*
* **Version Control:** Git & GitHub · CI is planned to be set up starting from Sprint 5 using GitHub Actions

## Installation

```bash
git clone https://github.com/bianh13/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation.git
cd "AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation"

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt   # to be updated as dependencies are added
```

## Team Workflow

* **Backlog & Board:** *[TO BE FILLED — GitHub Projects link]*
* **Branching:** `feature/<description>` → Pull Request into `main` → at least 1 review is required before merging
* **Commit Messages:** `USxx: short description` (following the corresponding user story)

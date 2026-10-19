# Buy/auth/simulation handoff — #76

Status: **partly works**, awaiting the real #81 portfolio transition and peer
acceptance. This branch targets main independently of #60: it contains the shared
quote schema/list API, buy UI and explicit simulation, but no provider worker,
stream command or websockets dependency. PR #94's reviewed extraction is retained.

## Boundaries

- orders/routes.py handles HTTP and translates the account module's AuthError
  using its original code/message/status. A guest sees login/register links.
- orders/service.py owns validation, preview and execute_buy, without Flask/SQL.
- orders/repository.py owns SQL and one write transaction with rollback. Session
  expiry/idle/revocation/status and price/cash are rechecked in that transaction.
- accounts installs real orders_identity and orders_csrf_token callbacks through
  init_auth; no test identity is installed. Missing callbacks still fail closed.
- simulation initializes a new exclusive DB or refreshes existing simulation
  observations, preserving balances/holdings/trades and invalidating old previews.

## Verified on 18 October 2026

125 automated tests passed, 2 existing sell placeholders skipped. Regression
tests use real SQLite and include real registration/session/CSRF integration,
two-account isolation, idle/absolute expiry, revocation/disabled accounts, foreign
origin, rollback, concurrent overspend, quote freshness/change and migration reruns.
The old empty auth-grant skip is removed because tests/test_auth.py covers it.

`python scripts/check_buy_ui.py` passed with actual headless Edge and a temporary
database: visible guest guard → Register → Market → Buy shares; 4,000 HPG warns
of a 12,000,000 VND shortfall, correction to 1,000 permits a 28,000,000 VND fill
and displays 72,000,000 cash plus 1,000 held shares. Logout/login preserves cash.
Manual generation refreshes quotes. An intercepted response is dropped AFTER
the server commits a second order; the form locks and never submits a duplicate.
This is author evidence, not independent-machine #83 or full-journey #82 evidence.

## Remaining handoffs

Long owns portfolio #81. The factory exposes portfolio_url only if a real GET
/portfolio route is registered; market/trade templates then show links for
signed-in users. This route-discovery test is a contract fixture, not portfolio
acceptance. Re-run the real browser journey through that screen when Long lands it.

Tue owns sell #79; use the existing preview and unit of work and coordinate changes
to shared form/routes. The #75 contract is approved in #91. Vu owns market search/
detail #85 and the dossier #86; no stock-detail implementation is claimed here.
Do not close #76 or mark the entire M3 flow works before integration and review.

The [20 October evidence](buy-acceptance.md) adds saved browser captures,
machine-readable results, a stale-quote/recovery check, and fixes for the stuck
preview-loading text and the obsolete cash estimate after a successful purchase.
It retains the Portfolio and independent-acceptance boundaries above.

## Reproduce

Follow docs/SETUP.md for a new simulation DB and real UI registration. Optional
Windows/Edge smoke: install playwright==1.63.0 in the development venv, then run
python scripts/check_buy_ui.py. It creates a disposable random password locally,
does not print it, never replaces auth callbacks and never calls DNSE/broker APIs.

Author clean-clone check on 18 October: local clone of commit `bb2e28f`, new
Python 3.10 venv, editable install plus pytest/ruff, copied .env.example, init-db
and init-demo succeeded. Full suite: 125 passed, 2 sell placeholders skipped;
Ruff passed. `websockets` was absent from this environment. This was a fresh
checkout on the author's machine, not the independent machine required by #83.

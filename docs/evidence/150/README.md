# Issue 150 Codespaces evidence

## Final acceptance run - 11 November 2026

2-core Codespace `super-duper spork` created from `main` at `f8b73af`
(Southeast Asia, 32 GB). The devcontainer built, `postCreateCommand` created
`.venv` and copied `.devcontainer/demo.env` to `.env`, and
`postAttachCommand` started `.venv/bin/python -m virtutrade run`. Port 5000
was forwarded automatically and `/market` loaded on the public HTTPS URL.

Flow with a new account:

- Register: market page, 100,000,000 VND.
- Login: accepted.
- `/market/HPG`: 401 daily candles, latest 11 Nov 2026.
- Buy 10 HPG, then sell 5 HPG: both orders completed.
- Portfolio: 5 HPG, cash 99,860,250 VND.

Screenshots are in `main/`:

- `01-register-filled.png` - register form, password masked.
- `02-register-success.png` - market page after registration, 100,000,000 VND.
- `03-login-success.png` - logged in after logout and login.
- `04-chart-hpg.png` - HPG chart with 401 candles.
- `05-buy-preview.png`, `06-buy-done.png` - buy 10 HPG.
- `07-sell-preview.png`, `08-sell-done.png` - sell 5 HPG.
- `09-portfolio.png` - 5 HPG holding and cash balance.

The Codespace was stopped after the run. It was active for about 15 minutes on
a 2-core machine, roughly 0.5 core-hours. GitHub billing showed `<$0.01` gross
for 11 Nov at the time of checking, with `$0` billed after included usage.

## Rehearsal run - 8 November 2026

Captured on a 2-core Codespace created from `feature/live-market-charts` at
`10373a8` (PR #151), before #147 merged. This was a rehearsal, not acceptance.

- `codespace-01-chart-hpg.png`: `/market/HPG` renders 401 daily candles.
- `codespace-02-register-error.png`: `/register` returned 403 `CSRF_FAILED`
  with "Invalid or missing CSRF token" after a valid email and password.
- `codespace-03-login-error.png`: `/login` returned the same 403.

Root cause: the Codespaces proxy rewrites `Origin` to
`http://localhost:5000` while `request.host` is the forwarded host, so
`same_origin_ok()` rejected a valid pre-auth CSRF token (issue #152). PR #157
fixed it and the final run above confirms register and login now work.

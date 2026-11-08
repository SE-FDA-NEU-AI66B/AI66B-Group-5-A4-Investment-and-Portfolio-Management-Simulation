# Issue 150 Codespaces rehearsal evidence

Captured 8 November 2026 on a 2-core Codespace created from the
`feature/live-market-charts` branch at `10373a8` (PR #151), not from `main`.
`main` at `0e51df1` still has no `.devcontainer`, so this is a rehearsal for
#150, not the final acceptance run.

- `codespace-01-chart-hpg.png`: `/market/HPG` renders 401 daily candles on port 5000.
- `codespace-02-register-error.png`: `/register` returns 403 `CSRF_FAILED` with
  "Invalid or missing CSRF token" after a valid email and 8+ character password.
- `codespace-03-login-error.png`: `/login` returns the same 403.

The devcontainer built, `postCreateCommand` copied `.devcontainer/demo.env` to
`.env`, `postAttachCommand` started the app, and port 5000 was forwarded
automatically. The failure is the Codespaces proxy rewriting `Origin` to
`http://localhost:5000` while `request.host` is the forwarded host, so
`same_origin_ok()` rejects the request. See #152.

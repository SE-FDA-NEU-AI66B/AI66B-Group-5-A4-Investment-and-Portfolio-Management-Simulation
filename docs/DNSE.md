# DNSE market-data worker — #59

This optional worker authenticates only to DNSE's market-data WebSocket and
subscribes to G1 equity tick/reference streams. It sends no broker orders, OTPs,
trading tokens or account instructions. The browser calls our read-only quote
API; credentials stay in the worker's environment and never enter JSON/HTML.

## Run locally

Follow SETUP first and install the checkout with `python -m pip install -e .`.
The runtime pins `websockets==15.0.1`. Stop processes using an existing database
and make a copy before upgrading it; point DATABASE_PATH at that copy and run
`python -m virtutrade init-db`. Verify rows/IDs before choosing that copy as the
working DB. Do not experiment on the only copy of a developer database.

The upgrade is an atomic feature migration: nullable quote reference, two
instrument reference fields and `feature_migration` ledger entry
`dnse-reference-v1`. It preserves IDs/rows and leaves auth's `PRAGMA user_version`
untouched. Failed migration rolls back DDL; a repeated successful run is harmless.

Put DNSE_API_KEY and DNSE_API_SECRET in the local ignored `.env` at the checkout
root. DNSE_SYMBOLS is a comma-separated selection of seeded equity symbols,
for example HPG,FPT; at most 100 symbols (two streams each). Never share the file.

```text
python -m virtutrade init-db
python -m virtutrade stream
```

In a separate terminal using the same venv/configuration:

```text
python -m virtutrade run
```

Open the SETUP market URL. The page polls GET `/api/market/quotes` every three
seconds, preserving the last table on failure and labelling source/time/staleness.
An initial 503 also keeps a polling target so it can recover when storage returns.
Polling the stored snapshot is not proof that the provider stream is connected.

## Boundaries and handoff

`dnse/worker.py` owns validation/authentication/reconnect; `dnse/repository.py`
owns newer-only writes. `market/service.py` derives percentage/freshness and
`market/routes.py` maps HTML/JSON responses. Vu's #85 extends these same endpoints
for search/detail; do not register a second list handler. The worker is a separate
process, so its failure does not stop Flask from showing the last stored snapshot.

Tick prices are converted from the G1 equity payload's thousands of VND using
Decimal. Nanoseconds remain in stored timestamps for ordering. Seed references
are never used for DNSE prices: until a provider reference for the same Vietnam
date exists, reference and change are null and the UI says Reference unavailable.
Unsupported/malformed/older/duplicate events cannot overwrite newer observations.
Provider error text is not logged because it may echo credentials; authentication
or subscription rejection stops safely. Network closures reconnect with fresh
authentication/subscription and a 1–60 second bounded backoff.

No historical REST bootstrap is included. Reference streams may not emit on
every connection; missing reference stays explicit rather than invented.

## Verification status — 10 October 2026

The resumed branch ports the original PR #60 without rewriting its history and
includes current main, including the teammate's #80 migration-contract tests.
Local tests cover a real localhost WebSocket handshake, reconnect, ping/pong,
signatures, malformed events, ordering, null/date-boundary references, persistent
reads, migration preservation/rollback and safe API failures.

A bounded **real DNSE** probe on 10 October used local credentials and a temporary
database: authentication succeeded and subscription was acknowledged. No tick or
reference event arrived in the 25-second observation window, and no DNSE quote
was persisted. This is proof of access only, **not** end-to-end live quote accuracy.
Raw auth payloads and secrets were neither printed nor saved.

Still required for #59: run while subscribed instruments emit events, verify a
persisted tick and compare symbol/price unit/value/provider timestamp with the
DNSE board, then exercise disconnect/restart and obtain independent review.
Record the exact tested commit, observation time and public quote evidence;
leave #59 open until these checks pass. Five existing money-rule integration
tests are skipped because the trading service has not landed; they are not DNSE
acceptance evidence and are tracked under #76/#79.

Protocol references: [DNSE market-data guide](https://developers.dnse.com.vn/docs/guide/market-data/connect/)
and [official Python client](https://github.com/dnse-tech/openapi-sdk/blob/main/python/dnse/websocket/client.py).

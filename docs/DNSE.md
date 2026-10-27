> PR #60 is merged into `main` at `17c7214` (20 October 2026).
> Run the worker from that revision or later; use a provider database separate
> from simulation quotes.

# DNSE market-data worker — #59

This optional worker authenticates to DNSE's market-data WebSocket and signed
latest-trade REST endpoint, subscribing to G1 equity tick/reference streams.
It sends no broker orders, OTPs,
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
root. Set `QUOTE_MODE=dnse` in **both terminals** to exclude demo prices from
Market, the stock picker and virtual order requests. Use
`DATABASE_PATH=instance/dnse.db`, separate from simulation.
DNSE_SYMBOLS is a comma-separated selection of known equity symbols;
leave it empty to receive all instruments in the database (12 initially),
or set e.g. `HPG,FPT,MWG`; at most 100 symbols (two streams each).
Never share the file.

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

`dnse/snapshot.py` owns signed read-only REST requests and periodic catch-up;
`dnse/worker.py` owns WebSocket validation/authentication/reconnect; `dnse/repository.py`
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

### Explicit retry policy

| Condition | Worker behavior | Recovery |
|-----------|-----------------|----------|
| Network/timeout/WebSocket exception, or normal socket closure | Reconnect with 1–60 second backoff; authenticate and subscribe again | Automatic; last stored quotes remain available |
| `auth_error` | Stop with a fixed authentication error | Check credentials/access, then restart |
| Provider `error`, before or after subscription | Stop with a fixed provider-error message | Check subscription/access and provider status, then restart |
| Invalid welcome/protocol, or SQLite failure | Stop rather than discard accepted data | Correct the protocol/storage problem before restart |
| Malformed/unsupported market event | Reject that event and continue | No price overwrite |

Stopping on provider `error` is intentional and is **not limited to auth failures**.
The reviewed [official client](https://github.com/dnse-tech/openapi-sdk/blob/main/python/dnse/websocket/client.py)
does not establish a retryable-code contract used by this adapter. We do not
infer recoverability from free-form provider messages. Consequently, an explicit
error caused by a temporary provider problem also needs an operator restart;
automatic recovery currently covers transport/session closure only. A later
retryable-error allowlist needs documented provider semantics and tests first.
Tests exercise fatal errors before/after subscription through `run_feed`, assert
no retry and unchanged quotes, and verify provider payloads are not echoed.

### Latest prices outside trading hours

`stream` starts both WebSocket ingestion and a latest-trade refresh immediately.
It calls only `GET https://openapi.dnse.com.vn/price/{symbol}/trades/latest?boardId=G1`,
then repeats one pass 60 seconds after the previous pass finishes.
Requests run outside the async event loop, with a 10-second timeout per symbol,
verified TLS, redirects disabled and a 64 KiB response limit.
The signing protocol and pinned `version: 2026-07-23` follow the
[official SDK](https://github.com/dnse-tech/openapi-sdk/blob/main/python/dnse/api/common.py).
The [latest-trade API](https://developers.dnse.com.vn/docs/dnse/get-latest-trades/)
returns the last trade even when no new tick arrives after startup.

REST `time` is `YYYY-MM-DD HH:mm:ss.SSS` in GMT+7 per the official schema;
it is stored as UTC with nine fractional digits for comparison with WebSocket events.
G1 `matchPrice` is converted from thousands of VND with Decimal, never floats.
An older REST response cannot overwrite a newer WebSocket tick.
Fetching tonight does **not** change an afternoon trade's timestamp or make it fresh:
the latest available price remains visible, while the existing 15-minute order
freshness rule continues to block stale-price purchases/sales.

Empty, malformed and failed responses preserve the last stored quote.
REST 401/403 stops the worker with a fixed message; timeouts, rate limiting and
other HTTP failures retry on the next pass without echoing provider bodies.
A missing symbol stays absent in DNSE mode until valid data arrives, never
replaced with a seed price. Demo mode remains available separately.

Reference streams may not emit on every connection; missing reference stays
explicit rather than invented. REST security definitions are deliberately not
used as an automatic daily-reference fallback: the 20 October evening probe
returned reference updates after 20:00, without an explicit trading date,
so assigning them to the afternoon trade could invent a daily change.

### Latest-trade verification — 20 October 2026

The authenticated REST catch-up refreshed all 12 instruments on the isolated
provider preview; WebSocket authentication and both subscriptions succeeded.
MWG returned `74.9` at `2026-10-20 14:45:03.431`, persisted/displayed as
`74,900 VND` at `2026-10-20T07:45:03.431000000Z`; FPT was `57,400 VND` and
HPG `21,100 VND`. The web/API comparison is recorded in
[the sanitized report](evidence/dnse-latest-2026-10-20.json).
These are the latest available afternoon trades, not new evening ticks.

The report is author integration evidence. The PO (`bianh13`) also confirmed
MWG/FPT/HPG against the official DNSE board in chat on 20 October; the exact
board-observation time and a browser capture were not supplied.
This comparison is explicitly recorded as PO-reported, not automated or an
independent code review. Independent review and merge of this follow-up remain
required before closing #59.

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


## Recheck — 18 October 2026

The feed branch integrates main commit 25aff26, including real auth and its
account migration; merge conflicts are resolved. Local suite: 120 passed,
5 pre-existing money-rule placeholders skipped. No broker-order/OTP endpoint exists.

A read-only probe started at 2026-10-18T16:08:49Z (23:08:49 UTC+7), using local
credentials and a temporary DB. Authentication and subscription acknowledgement
succeeded. During the bounded 25-second observation: zero tick events, zero
reference events, zero persisted DNSE quotes. No secret or raw payload was logged.
This verifies access only. Quote value/unit/provider-time comparison and live
disconnect/restart acceptance still need an observation with actual events;
#59 and #60 remain incomplete and must not be marked accepted from these results.

## Live ticks and controlled restart — 19 October 2026

Tested application commit: `31d4f0a2db81e33567bddfbd412d0419ab94799d`.
The [sanitized observation report](evidence/dnse-live-2026-10-19.json) records
only public quote fields, counters and verification outcomes; it contains no
credentials, account data or raw authentication payloads.

At 10:43:31 UTC+7, a 25-second read-only session authenticated, subscribed and
received five tick events. SQLite stored FPT at 57,800 VND and HPG at 20,900 VND
with original provider timestamps and `source=dnse`. These are observations at
those timestamps, not current-price promises or independently verified values.

A separate temporary database was then used for two 25-second sessions starting
at 10:44:51 and 10:45:16 UTC+7. The first received seven ticks. After stopping
that connection, recreating Flask over the same database preserved the exact
stored rows and `/api/market/quotes` still returned HTTP 200. A newly authenticated
and subscribed connection received nine more ticks; the API then exposed FPT at
57,700 VND and HPG at 20,950 VND with fresh provider timestamps and `stale=false`.
The market HTML route returned HTTP 200 after each session. This verifies a
controlled stop/reconnect and application recreation, not a real network-outage
backoff test or a browser rendering test. Automated local-server tests cover
the reconnect/backoff behavior separately.

Neither probe received reference events, so live `previous_close_vnd` and
`change` correctly remained null. Comparison against the public DNSE board
has not been completed: no browser connection was available in this session.
The final price/unit comparison acceptance criterion and independent review
remain unchecked; #59 stays open with zero completed points.

### Outstanding board comparison and reference verification

The `x1000` conversion is the adapter's G1 equity unit assumption. The observed
57,800/20,900 VND values and the [DNSE equity example](https://developers.dnse.com.vn/docs/guide/market-data/connect/)
are consistent with it, but do not independently verify it against the board.
Before acceptance, record a matching ticker and observation time, the raw
provider price/timestamp, the stored/API VND price, and the board price with
its displayed unit; include the board URL/screenshot and exact tested commit.
A current board quote cannot prove the value of an earlier intraday tick.

The [provider guide](https://developers.dnse.com.vn/docs/guide/market-data/connect/)
describes security definitions as scheduled batch data rather than per-tick
updates. Our midday probes received no such event. Missing-reference behavior
is covered by tests and displays unavailable; same-day live reference/change
comparison remains unverified. Neither the ready flag nor passing CI closes
these external verification items. No board comparison was completed during
this review follow-up because no connected browser was available.

## Main integration - 20 October 2026

PR #60 was independently approved for worker integration and merged at
`17c7214`, after the UI PR #102. The exact combined tree was tested locally:
193 passed, 2 existing skips; Ruff and whitespace checks passed.

An isolated copy runs the new UI and worker against the same provider database.
At 16:44 UTC+7 the worker authenticated and DNSE acknowledged tick/reference
subscriptions for all 12 seeded symbols. No new tick was observed during this
check. Browser verification confirmed that the API's stored FPT/HPG values,
original timestamps, source and stale labels match the table; this is not a
new live-price or provider-board comparison. Seed rows remain explicitly seed.

Keep #59 open at zero completed points until the outstanding provider-board
unit/value/timestamp comparison and independent live acceptance are complete.
The code approval and merge do not waive those criteria.

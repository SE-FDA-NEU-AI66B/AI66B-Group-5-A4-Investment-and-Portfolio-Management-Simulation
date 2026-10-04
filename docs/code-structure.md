# Code structure

The application uses business modules with separate presentation, service and
data-access files inside each module. `virtutrade/` is the Python source package
(the role played by `src/` in the instructor's example); `market/` is the first
implemented business module. Small layers are single files, as allowed in the
slides. Flask's Blueprint combines routing and controller responsibilities.

```text
README.md                      Entry point with SETUP link
requirements.txt               Versioned runtime dependency
.env.example                   Safe configuration, committed
.gitignore                     The single effective ignore file
data/demo-quotes.json           Initial data, committed
app.py                         Thin CLI: run / init-db
database.py                    Compatibility exports, no SQL implementation
virtutrade/
  __init__.py                  Application factory, dependency wiring and registration
  config.py                    Local configuration and repository-relative paths
  database/
    schema.py                  Shared six-table schema
    seed.py                    Repeatable initialization from data/demo-quotes.json
  market/
    __init__.py                Exports the market Blueprint
    routes.py                  URL/controller, HTML response and HTTP status
    service.py                 Percentage/staleness rules and QuoteReader interface
    repository.py              SQLite query, row mapping and storage error translation
    models.py                  Immutable quote data and display results
    errors.py                  Market failure shared between repository/controller
    templates/market/index.html
    static/market.css
tests/
  test_market.py               Snapshot behavior and persistence
  test_erd_constraints.py      Independent ERD constraint checks
  test_modules.py              Asset/path relocation and application isolation
  test_market_layers.py        Service rules and request failure/recovery boundaries
docs/                          Design, SETUP, process evidence and images
scripts/diagram.py             Diagram maintenance, outside application runtime
```

Request flow: browser → market route → service → repository → SQLite, then
the route renders the market template. Its stylesheet is served at
`/market/static/market.css`. `/` still redirects to `/market`; setup and CLI
commands are unchanged. Internal Python calls connect these layers; no extra
HTTP server is needed between folders.

## Layer responsibilities

| Layer | Does | Must not do |
|-------|------|-------------|
| Route/controller | Obtain the configured reader, call the service, render HTML, map `MarketDataUnavailable` to 503 | Import SQLite, run SQL, calculate percentage/staleness rules |
| Service | Read through the `QuoteReader` interface, calculate exact percentage change and the 15-minute stale threshold | Read Flask requests/config, choose a database, run SQL, return HTTP responses |
| Repository | Execute the query, map rows to `Quote`, translate SQLite errors to `MarketDataUnavailable`, close its connection | Choose HTTP codes, render templates, decide stale-price rules |
| Models | Describe immutable quote inputs and service output | Read HTTP, execute queries or apply business rules |
| Application factory | Select the concrete repository and register modules | Query the database during app creation |

The SQL schema in `virtutrade/database/schema.py` remains the single definition
of all six tables and their constraints. `Quote` is the joined read projection
of instrument/price_quote, and `MarketQuote` adds the service's display result;
they are not ORM tables or duplicated schema definitions. No ORM is needed for
this SQLite slice. Other entities gain Python models when their services need them.

The factory injects a SQLite reader into each market request. A unit test can
supply an in-memory reader to `market_snapshot` with a fixed clock, without a
Flask application context or database. A later PostgreSQL adapter can implement
the same interface: service and controller logic remain unchanged, while the
repository wiring and database initialization/migration code must be adapted.

## Failure boundaries

SQLite failures are caught at the repository boundary; the controller returns
the existing market-only 503 page and does not expose internal error details.
Connections close after each read, and no database is opened at application
startup. Tests demonstrate that an unavailable market reader does not prevent
an independent test route or the stylesheet from responding, and that a later
request recovers when the reader becomes available.

This is request-level containment, not a guarantee of independent availability.
Modules still share one process and database; process crashes, resource exhaustion
or a shared database outage can affect several features. The future DNSE worker
remains a separate process under ADR-2, keeping its connection/reconnect loop
outside the web server.

| Problem | Start here |
|---------|------------|
| Page layout or text | `virtutrade/market/templates/market/index.html` |
| Styling | `virtutrade/market/static/market.css` |
| URL, response status or error page | `virtutrade/market/routes.py` |
| Change percentage or delayed-price warning | `virtutrade/market/service.py` |
| Rows, joins or database reads | `virtutrade/market/repository.py` |
| Tables, constraints or initial demo rows | `virtutrade/database/` |
| Database location or module registration | `virtutrade/config.py`, `virtutrade/__init__.py` |

Future account, order, portfolio and Admin features should follow the same
feature-folder pattern and register their Blueprints in the factory. They are
API designs for M2, not implemented features or empty placeholder modules.
Add authentication/permission middleware when those private routes are built;
keep shared helpers in `utils` only when they have no business-specific rules.
Root `database.py` re-exports the existing API so the independent ERD tests and
existing callers still work; new code imports the package directly. Existing
ERD images citing `database.py::SCHEMA` refer to that compatibility export; the
canonical definition is now `virtutrade/database/schema.py`.

Root `app.py` is retained so SETUP's `python app.py init-db` and `python app.py`
commands keep working. The old file named `gitignore` was consolidated into
`.gitignore`; only the latter controls Git's ignore rules. Runtime `.env` and
SQLite files are local and ignored. Schema, seed data and initialization code
are committed so every machine can create its own database with one command.

## DNSE SDK reference and M2 scope

Reviewed the user's [Python SDK fork at revision df6bcca](https://github.com/bianh13/openapi-sdk/tree/df6bcca71ef6fb9be3d14689dd0c070c228b16c1/python),
including its README, `marketdata-api/get_security_definition.py` and
`websocket-marketdata/trade.py`. The latter subscribes to executed-trade market
events; it does not submit an order. Market-data examples and the `trading-api`
examples serve different purposes and must not be copied together indiscriminately.
The fork identifies `dnse-tech/openapi-sdk` as its upstream.

M2's required slice reads 12 seeded quotes from a real SQLite database and
labels them as demo data. It needs no DNSE key, secret, token, OTP or live feed.
This application does not import the SDK or contact DNSE, and it has no broker
order submission route. The SDK examples were inspected, not executed.

Optional live-feed issue #59 is carried over to Sprint 3; PR #60 is temporarily
closed without merging, with its branch/code retained. It remains separate from this slice.
If resumed, its provider adapter should be a separate module/process feeding
stored quotes, consistent with ADR-2; it must use market-data operations only.
Review and adapt that draft to the new package layout before integrating it.

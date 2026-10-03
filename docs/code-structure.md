# Code structure

The M2 application groups each page's HTTP routes, presentation logic, database
queries, template and stylesheet in one feature folder. This implements the
instructor's module-packaging feedback without expanding the required demo.

```text
app.py                         CLI: run / init-db
database.py                    Compatibility exports for existing callers
virtutrade/
  __init__.py                  Application factory and module registration
  config.py                    Local configuration and repository-relative paths
  database/
    schema.py                  Shared six-table schema
    seed.py                    Repeatable initialization from data/demo-quotes.json
  market/
    __init__.py                Exports the market Blueprint
    routes.py                  GET /market and HTTP error handling
    service.py                 Percentage change and stale-price status
    repository.py              Read-only SQLite snapshot query
    templates/market/index.html
    static/market.css
tests/
  test_market.py               Snapshot behavior and persistence
  test_erd_constraints.py      Independent ERD constraint checks
  test_modules.py              Asset/path relocation and application isolation
```

Request flow: browser → market route → service → repository → SQLite, then
the route renders the market template. Its stylesheet is served at
`/market/static/market.css`. `/` still redirects to `/market`; setup and CLI
commands are unchanged. Internal Python calls connect these layers; no extra
HTTP server is needed between folders.

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
Root `database.py` re-exports the existing API so the independent ERD tests and
existing callers still work; new code imports the package directly. Existing
ERD images citing `database.py::SCHEMA` refer to that compatibility export; the
canonical definition is now `virtutrade/database/schema.py`.

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

Optional live-feed issue #59 / draft PR #60 remains separate from this slice.
If resumed, its provider adapter should be a separate module/process feeding
stored quotes, consistent with ADR-2; it must use market-data operations only.
Review and adapt that draft to the new package layout before integrating it.

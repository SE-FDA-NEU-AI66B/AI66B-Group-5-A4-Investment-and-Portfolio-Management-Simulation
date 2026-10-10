# Account-state migration contract (#80)

Owner: @nguyentue110. Reviewer: @bianh13. Status: **proposal for #77 to
implement** — nothing below changes `src/` yet, so there is no double-counted
work with the auth implementation issue.

## Scope

US01 needs two things the M2 schema cannot store: server-side sessions (with
expiry and revocation, for login/logout and the disabled-account 403 rule) and
login counters (five wrong passwords lock an account for 15 minutes). This
document specifies that storage, the schema-version contract and the upgrade
proof. Login, logout, CSRF and Admin services themselves belong to #77.

## Required storage

Counters live on `account` (one counter set per account, no join needed):

```sql
ALTER TABLE account ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0
    CHECK(failed_attempts >= 0);
ALTER TABLE account ADD COLUMN locked_until TEXT;
```

`locked_until` is NULL when the account is not locked, otherwise a UTC ISO-8601
deadline. A successful login resets both fields to `0`/`NULL`.

Sessions live in a new table so logout and disabled-account revocation only
stamp a row instead of deleting history:

```sql
CREATE TABLE IF NOT EXISTS auth_session (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES account(id),
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
);
```

Store only the token hash, never the token. A session is active when
`revoked_at IS NULL AND expires_at > now`.

## Alternatives considered

- A separate `login_attempt` audit table (one row per attempt) was rejected:
  lockout needs a counter and a deadline, not a history, and US08-style attempt
  history is already deferred backlog.
- Plaintext session tokens were rejected: a database read must never yield a
  usable credential.
- CSRF needs no table: per-form tokens are validated server-side against the
  active session above.

## Versioning and applier contract

- M2 baseline is schema version 1; this upgrade records version 2 with
  `PRAGMA user_version` after a successful run.
- Raw `ALTER TABLE` is not rerunnable, so the implementation must use a
  guarded applier: skip when the version is already 2, check
  `PRAGMA table_info` before each `ADD COLUMN`, run inside one transaction
  with rollback on failure. The reference applier in
  `tests/test_account_migration.py` demonstrates the contract.
- SQLite ignores foreign keys declared by `ADD COLUMN`, so new FKs must arrive
  via new tables (as `auth_session` does), never via altered columns.
- Upgrade rule: **copy the database file first, migrate the copy, verify
  counts, then swap**. Never migrate a live developer database in place.

## References

- Source of truth today: `src/virtutrade/database/schema.py::SCHEMA`.
- Data model: `docs/design.md` section 2, `docs/images/erd.png`.
- Rules: BR5 (one-time grant, untouched by this change), BR9 (role/status
  checks and audit stay in service code; this change adds no authorization).
- Stories: US01 (lockout/session), US02 (grant path unchanged), US13 (revoke
  on disable).

## Verification summary (#80)

`tests/test_account_migration.py`, 9 tests, all passing
(`python -m pytest tests/test_account_migration.py -v`):

- Fresh M2 database accepts the upgrade with safe defaults and version 2.
- A copied M2 fixture (12 instruments/quotes with ids 1..12, one account,
  holding and trade) migrates with every id and row identical; the source copy
  keeps the old schema (copy-first proven).
- Reruns are no-ops returning False; versions and rows untouched.
- Lockout, session lifecycle/revoke/expiry, token uniqueness and FK rejection
  behave exactly as #77's service will assume.

## Handoff to #77

Move the statements and the guarded applier into `src/` behind the auth work,
keep the version scheme above, and do not count this proposal's points again.
Open question for the PO: none on storage — the remaining PO decisions are the
session lifetime values and lockout durations already specified in US01.

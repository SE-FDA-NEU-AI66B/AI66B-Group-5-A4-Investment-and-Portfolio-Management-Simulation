"""Simulation refresh rules; no HTTP or SQL."""

from datetime import datetime, timezone

from virtutrade.market.service import parse_timestamp
from virtutrade.orders.errors import OrderError


def refresh_quotes(session_id, unit_of_work, *, now=None):
    now = now or datetime.now(timezone.utc)
    with unit_of_work() as repo:
        account = repo.account_for_session(session_id)
        try:
            active = (
                account
                and not account.revoked_at
                and parse_timestamp(account.expires_at) > now
            )
        except (TypeError, ValueError, AttributeError):
            active = False
        if not active:
            raise OrderError(
                "AUTH_REQUIRED", "Sign in again before generating demo quotes."
            )
        if account.status != "active":
            raise OrderError(
                "ACCOUNT_DISABLED", "This account is disabled. Contact support."
            )
        rows = repo.quote_sources_and_times()
        if not rows or any(source != "simulation" for source, _ in rows):
            raise OrderError(
                "SIMULATION_DISABLED",
                "Demo generation is unavailable for this database. Use the local simulation setup.",
            )
        try:
            advancing = all(parse_timestamp(stamp) < now for _, stamp in rows)
        except (TypeError, ValueError, AttributeError):
            advancing = False
        if not advancing:
            raise OrderError(
                "SIMULATION_CLOCK_NOT_ADVANCED",
                "A new demo timestamp could not be generated. Wait a moment and try again.",
            )
        return repo.write_batch(now)

"""Value one account's holdings using the exact money rules.

Arithmetic follows docs/money-rules.md: integer VND throughout, Decimal only
where a division is unavoidable, explicit ROUND_HALF_UP, and no binary float.
The reference numbers are regression-tested in tests/test_money_rules.py; this
module is where they reach the screen.
"""

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from virtutrade.market.service import parse_timestamp
from virtutrade.portfolio.models import Portfolio, Position, ValuedPosition

# Same freshness window as the market page and order validation: older than
# 15 minutes, or more than 5 minutes in the future, is shown as delayed.
STALE_AFTER_SECONDS = 900
FUTURE_TOLERANCE_SECONDS = 300


class PortfolioReader(Protocol):
    """The only data-access operation needed by the portfolio service."""

    def fetch_snapshot(self, account_id: int) -> tuple[int, list[Position]]: ...


def is_stale(quoted_at: str | None, now: datetime) -> bool:
    """An unreadable or naive timestamp is treated as stale, never as fresh."""
    if quoted_at is None:
        return True
    try:
        age = (now - parse_timestamp(quoted_at)).total_seconds()
    except (TypeError, ValueError, AttributeError):
        return True
    return age > STALE_AFTER_SECONDS or age < -FUTURE_TOLERANCE_SECONDS


def value_position(position: Position, *, now: datetime) -> ValuedPosition:
    """Derive display values for one holding without touching HTTP or SQL."""
    # Average cost is the ratio of the stored totals, never a stored rounded
    # price (money-rules.md). Quantity is CHECK(quantity > 0) in the schema.
    average_cost = Decimal(position.cost_basis_vnd) / Decimal(position.quantity)

    if position.price_vnd is None:
        # No quote row: the holding exists but cannot be valued. Keeping these
        # as None keeps a missing price out of the totals, where treating it as
        # zero would silently understate the portfolio (US06-AC4).
        return ValuedPosition(
            **vars(position),
            average_cost_vnd=average_cost,
            market_value_vnd=None,
            unrealised_pnl_vnd=None,
            unrealised_pnl_percent=None,
            stale=True,
            priced=False,
        )

    market_value = position.quantity * position.price_vnd
    unrealised = market_value - position.cost_basis_vnd
    if position.cost_basis_vnd == 0:
        # money-rules.md: the return % is NULL when its denominator is zero.
        percent = None
    else:
        percent = (Decimal(unrealised) / Decimal(position.cost_basis_vnd) * 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

    return ValuedPosition(
        **vars(position),
        average_cost_vnd=average_cost,
        market_value_vnd=market_value,
        unrealised_pnl_vnd=unrealised,
        unrealised_pnl_percent=percent,
        stale=is_stale(position.quoted_at, now),
        priced=True,
    )


def build_portfolio(
    reader: PortfolioReader, account_id: int, *, now: datetime | None = None
) -> Portfolio:
    """Read one snapshot for `account_id` and derive every displayed value.

    The caller supplies the account id; this function never discovers it, so
    the session source cannot change which rows are read.
    """
    now = now if now is not None else datetime.now(timezone.utc)
    cash, rows = reader.fetch_snapshot(account_id)
    positions = [value_position(row, now=now) for row in rows]

    holdings_value = sum(p.market_value_vnd for p in positions if p.priced)
    return Portfolio(
        account_id=account_id,
        cash_vnd=cash,
        positions=positions,
        holdings_value_vnd=holdings_value,
        total_value_vnd=cash + holdings_value,
        unpriced_count=sum(1 for p in positions if not p.priced),
        stale_count=sum(1 for p in positions if p.priced and p.stale),
    )


def as_api_payload(portfolio: Portfolio) -> dict:
    """Serialise for `GET /api/portfolio`; Decimal becomes a string, not a float.

    A percentage sent as a JSON number invites a float round-trip on the
    client, so the exact displayed digits travel as text instead.
    """
    return {
        'cash_vnd': portfolio.cash_vnd,
        'holdings_value_vnd': portfolio.holdings_value_vnd,
        'total_value_vnd': portfolio.total_value_vnd,
        'valuation_complete': portfolio.unpriced_count == 0,
        'unpriced_count': portfolio.unpriced_count,
        'stale_count': portfolio.stale_count,
        'positions': [
            {
                'symbol': p.symbol,
                'name': p.name,
                'quantity': p.quantity,
                'cost_basis_vnd': p.cost_basis_vnd,
                'average_cost_vnd': str(p.average_cost_vnd),
                'price_vnd': p.price_vnd,
                'market_value_vnd': p.market_value_vnd,
                'unrealised_pnl_vnd': p.unrealised_pnl_vnd,
                'unrealised_pnl_percent': (
                    None if p.unrealised_pnl_percent is None else str(p.unrealised_pnl_percent)
                ),
                'quoted_at': p.quoted_at,
                'priced': p.priced,
                'stale': p.stale,
            }
            for p in portfolio.positions
        ],
    }
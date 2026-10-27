"""Immutable data read for one account and prepared for display.

These are read projections of account joined with holding and price_quote, not
an ORM or a second schema definition. Table constraints live in
database/schema.py; the money rules live in docs/money-rules.md.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Position:
    """One holding as stored, with the latest quote for its instrument.

    `price_vnd` and `quoted_at` are None when no quote row exists for the
    instrument. That is a real state, not a zero price: US06 requires an
    unpriced holding to be shown honestly rather than valued at nothing.
    """

    symbol: str
    name: str
    quantity: int
    cost_basis_vnd: int
    price_vnd: int | None
    quoted_at: str | None


@dataclass(frozen=True)
class ValuedPosition(Position):
    """A position with the derived display values from docs/money-rules.md."""

    average_cost_vnd: Decimal
    market_value_vnd: int | None
    unrealised_pnl_vnd: int | None
    unrealised_pnl_percent: Decimal | None
    stale: bool
    priced: bool


@dataclass(frozen=True)
class Portfolio:
    """Everything the page and `GET /api/portfolio` need for one account.

    `total_value_vnd` is cash plus the market value of priced holdings only.
    When `unpriced_count` is above zero the total is incomplete, and both the
    page and the API say so rather than quietly understating it.
    """

    account_id: int
    cash_vnd: int
    positions: list[ValuedPosition]
    holdings_value_vnd: int
    total_value_vnd: int
    unpriced_count: int
    stale_count: int
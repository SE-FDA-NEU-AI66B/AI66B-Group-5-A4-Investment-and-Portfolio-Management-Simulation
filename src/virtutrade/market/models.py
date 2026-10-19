"""Immutable data returned by the market query and prepared for display.

Quote is the read projection of instrument joined with price_quote, not an ORM
or a second schema definition. Table constraints live in database/schema.py.
"""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class Quote:
    symbol: str
    name: str
    price_vnd: int
    previous_close_vnd: int | None
    quoted_at: str
    source: str
    reference_at: str | None = field(default=None, kw_only=True)


@dataclass(frozen=True)
class MarketQuote(Quote):
    change: Decimal | None
    stale: bool

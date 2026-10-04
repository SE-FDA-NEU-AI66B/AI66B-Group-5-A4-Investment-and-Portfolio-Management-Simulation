"""Immutable data returned by the market query and prepared for display.

Quote is the read projection of instrument joined with price_quote, not an ORM
or a second schema definition. Table constraints live in database/schema.py.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Quote:
    symbol: str
    name: str
    price_vnd: int
    previous_close_vnd: int
    quoted_at: str
    source: str


@dataclass(frozen=True)
class MarketQuote(Quote):
    change: Decimal
    stale: bool

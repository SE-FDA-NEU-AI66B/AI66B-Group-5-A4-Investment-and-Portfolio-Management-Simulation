"""Prepare a stored market snapshot for display using exact percentage math."""

from dataclasses import asdict
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from virtutrade.market.models import MarketQuote, Quote


class QuoteReader(Protocol):
    """The only data-access operation needed by the market service."""

    def fetch_quotes(self) -> list[Quote]: ...


def market_snapshot(reader: QuoteReader, *, now: datetime | None = None) -> list[MarketQuote]:
    """Calculate display values without knowing HTTP, SQL or a database path."""
    now = now if now is not None else datetime.now(timezone.utc)
    snapshot = []
    for quote in reader.fetch_quotes():
        change = (Decimal(quote.price_vnd - quote.previous_close_vnd)
                  / Decimal(quote.previous_close_vnd) * 100)
        change = change.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        try:
            timestamp = datetime.fromisoformat(quote.quoted_at.replace('Z', '+00:00'))
            stale = timestamp.tzinfo is None or (now - timestamp).total_seconds() > 900
        except (ValueError, TypeError):
            stale = True
        snapshot.append(MarketQuote(**asdict(quote), change=change, stale=stale))
    return snapshot

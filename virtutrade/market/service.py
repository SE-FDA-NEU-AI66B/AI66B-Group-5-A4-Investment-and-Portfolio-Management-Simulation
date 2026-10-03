"""Prepare a stored market snapshot for display using exact percentage math."""

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from virtutrade.market.repository import read_market


def market_snapshot(database):
    quotes = read_market(database)
    now = datetime.now(timezone.utc)
    for quote in quotes:
        change = (Decimal(quote['price_vnd'] - quote['previous_close_vnd'])
                  / Decimal(quote['previous_close_vnd']) * 100)
        quote['change'] = change.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        try:
            timestamp = datetime.fromisoformat(quote['quoted_at'].replace('Z', '+00:00'))
            quote['stale'] = timestamp.tzinfo is None or (now - timestamp).total_seconds() > 900
        except (ValueError, TypeError):
            quote['stale'] = True
    return quotes

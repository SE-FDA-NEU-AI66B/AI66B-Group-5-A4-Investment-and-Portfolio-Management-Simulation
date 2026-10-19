"""Prepare quote values without HTTP or database dependencies."""

import re
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from virtutrade.market.models import MarketQuote, Quote

VIETNAM = timezone(timedelta(hours=7))


class QuoteReader(Protocol):
    def fetch_quotes(self) -> list[Quote]: ...


def parse_timestamp(value):
    # Python 3.10: trim only for display arithmetic; preserve raw nanoseconds in DB.
    value = re.sub(r"(\.\d{6})\d+", r"\1", value.replace("Z", "+00:00"))
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("Timezone required")
    return result


def market_snapshot(reader: QuoteReader, *, now=None) -> list[MarketQuote]:
    now = now or datetime.now(timezone.utc)
    result = []
    for quote in reader.fetch_quotes():
        values = asdict(quote)
        try:
            stamp = parse_timestamp(quote.quoted_at)
            age = (now - stamp).total_seconds()
            stale = age > 900 or age < -300
        except (ValueError, TypeError, AttributeError):
            stamp, stale = None, True
        reference = quote.previous_close_vnd
        if quote.source == 'dnse':
            try:
                ref_time = parse_timestamp(quote.reference_at)
                if stamp is None or ref_time.astimezone(VIETNAM).date() != stamp.astimezone(VIETNAM).date():
                    reference = None
            except (ValueError, TypeError, AttributeError):
                reference = None
        change = None
        if reference is not None and reference > 0:
            change = (Decimal(quote.price_vnd - reference) / reference * 100).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP)
        values['previous_close_vnd'] = reference
        result.append(MarketQuote(**values, change=change, stale=stale))
    return result

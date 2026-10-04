"""Business-rule tests use an in-memory reader; HTTP mapping is checked separately."""

import sqlite3
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from virtutrade import create_app
from virtutrade.market.errors import MarketDataUnavailable
from virtutrade.market.models import Quote
from virtutrade.market.repository import SQLiteQuoteRepository
from virtutrade.market.service import market_snapshot

NOW = datetime(2026, 10, 4, 9, 30, tzinfo=timezone.utc)
QUOTE = Quote('HPG', 'Hoa Phat', 28000, 27500, '2026-10-04T09:15:00Z', 'seed')


class MemoryQuotes:
    def __init__(self, quote=QUOTE):
        self.quote = quote

    def fetch_quotes(self):
        return [self.quote]


@pytest.mark.parametrize(('timestamp', 'stale'), [
    ('2026-10-04T09:15:00Z', False),  # Exactly 15 minutes is still within the limit.
    ('2026-10-04T09:14:59Z', True),
    ('2026-10-04T09:29:00', True),  # A timestamp without timezone is not trusted.
    ('invalid', True),
])
def test_service_staleness_without_http_or_database(timestamp, stale):
    quote = replace(QUOTE, quoted_at=timestamp)
    result = market_snapshot(MemoryQuotes(quote), now=NOW)[0]
    assert result.stale is stale
    assert result.quoted_at == timestamp and result.source == 'seed'


@pytest.mark.parametrize(('price', 'change'), [(33, '3.13'), (31, '-3.13')])
def test_service_rounds_percentage_without_mutating_stored_quote(price, change):
    quote = replace(QUOTE, price_vnd=price, previous_close_vnd=32)
    result = market_snapshot(MemoryQuotes(quote), now=NOW)[0]
    assert result.change == Decimal(change)
    assert result.price_vnd == quote.price_vnd == price
    assert quote.previous_close_vnd == 32
    assert not hasattr(quote, 'change')


def test_repository_translates_storage_failure_and_does_not_create_database(tmp_path):
    path = tmp_path / 'missing.db'
    with pytest.raises(MarketDataUnavailable) as error:
        SQLiteQuoteRepository(path).fetch_quotes()
    assert isinstance(error.value.__cause__, sqlite3.Error)
    assert not path.exists()


def test_market_failure_does_not_break_other_route_or_prevent_recovery():
    class UnavailableQuotes:
        def fetch_quotes(self):
            raise MarketDataUnavailable('internal provider details')

    app = create_app({'TESTING': True})
    app.extensions['market_reader_factory'] = UnavailableQuotes

    @app.get('/independent-feature')
    def independent_feature():
        return 'still available'

    client = app.test_client()
    response = client.get('/market')
    assert response.status_code == 503
    assert b'Market data is unavailable' in response.data
    assert b'internal provider details' not in response.data
    assert client.get('/independent-feature').status_code == 200
    assert client.get('/market/static/market.css').status_code == 200
    app.extensions['market_reader_factory'] = MemoryQuotes
    recovered = client.get('/market')
    assert recovered.status_code == 200
    assert b'28,000' in recovered.data and b'+1.82%' in recovered.data

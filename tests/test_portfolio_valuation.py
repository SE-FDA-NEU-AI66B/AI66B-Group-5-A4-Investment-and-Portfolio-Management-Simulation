"""Valuation for US06, tested with an in-memory reader: no HTTP, no database.

The money numbers here are the ones US06 names, and they are the same figures
tests/test_money_rules.py locks down for the arithmetic itself. If those two
files ever disagree, the service is wrong.

The real SQLite read path and the HTTP surface are tested in
tests/test_portfolio.py.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from virtutrade.portfolio.models import Position
from virtutrade.portfolio.service import as_api_payload, build_portfolio, value_position

NOW = datetime(2026, 10, 10, 9, 30, tzinfo=timezone.utc)
FRESH = '2026-10-10T09:20:00Z'

# US06-AC2: 200 HPG at 30,000 average cost, quoted at 33,000.
HPG = Position('HPG', 'Hoa Phat Group', 200, 6_000_000, 33_000, FRESH)


class MemoryPortfolio:
    """Satisfies the PortfolioReader protocol without SQL or a database file."""

    def __init__(self, cash=40_000_000, positions=(HPG,), account_id=1):
        self.cash = cash
        self.positions = list(positions)
        self.account_id = account_id
        self.asked_for = []

    def fetch_snapshot(self, account_id):
        self.asked_for.append(account_id)
        if account_id != self.account_id:
            return self.cash, []
        return self.cash, self.positions


def test_us06_reference_valuation():
    """200 @ 30,000 cost, quoted 33,000 -> 6,600,000 value, +600,000, +10.00%.
    With 40,000,000 cash the total is 46,600,000 (US06-AC2, BR6)."""
    portfolio = build_portfolio(MemoryPortfolio(), 1, now=NOW)
    position = portfolio.positions[0]

    assert position.average_cost_vnd == Decimal(30_000)
    assert position.market_value_vnd == 6_600_000
    assert position.unrealised_pnl_vnd == 600_000
    assert position.unrealised_pnl_percent == Decimal('10.00')
    assert portfolio.holdings_value_vnd == 6_600_000
    assert portfolio.total_value_vnd == 46_600_000
    assert portfolio.unpriced_count == 0


def test_empty_account_total_is_cash_only():
    """US06-AC3: no holdings means the total equals cash."""
    portfolio = build_portfolio(MemoryPortfolio(positions=()), 1, now=NOW)
    assert portfolio.positions == []
    assert portfolio.holdings_value_vnd == 0
    assert portfolio.total_value_vnd == 40_000_000


def test_missing_quote_is_not_a_zero_value_holding():
    """US06-AC4: an unpriced holding must not be valued at nothing. It stays
    visible, its derived values are None, and it is excluded from the total,
    which is then reported as incomplete."""
    unpriced = Position('SSI', 'SSI Securities', 100, 3_200_000, None, None)
    portfolio = build_portfolio(MemoryPortfolio(positions=(HPG, unpriced)), 1, now=NOW)
    ssi = next(p for p in portfolio.positions if p.symbol == 'SSI')

    assert ssi.priced is False
    assert ssi.market_value_vnd is None
    assert ssi.unrealised_pnl_vnd is None
    assert ssi.quantity == 100 and ssi.cost_basis_vnd == 3_200_000
    assert ssi.average_cost_vnd == Decimal(32_000)
    # The total counts HPG only, and says so rather than understating silently.
    assert portfolio.total_value_vnd == 46_600_000
    assert portfolio.unpriced_count == 1


@pytest.mark.parametrize(('quoted_at', 'stale'), [
    (FRESH, False),
    ('2026-10-10T09:15:00Z', False),  # Exactly 15 minutes is still within the limit.
    ('2026-10-10T09:10:00Z', True),
    ('2026-10-10T09:20:00', True),    # A timestamp without timezone is not trusted.
    ('2026-10-10T09:34:00Z', False),  # Up to 5 minutes ahead is clock skew.
    ('2026-10-10T09:36:00Z', True),   # Further ahead is not trusted.
    ('nonsense', True),
])
def test_delayed_quotes_are_flagged_but_still_valued(quoted_at, stale):
    """A delayed price is shown honestly, not dropped: the holding still has a
    market value, with the staleness recorded alongside it."""
    position = value_position(
        Position('HPG', 'Hoa Phat Group', 200, 6_000_000, 33_000, quoted_at), now=NOW
    )
    assert position.stale is stale
    assert position.priced is True
    assert position.market_value_vnd == 6_600_000


def test_loss_is_signed_and_rounded_half_up():
    """50 FPT at 130,000 average cost quoted at 120,000 is -500,000, -7.69%
    (-7.6923... rounds half up to two places)."""
    position = value_position(
        Position('FPT', 'FPT Corporation', 50, 6_500_000, 120_000, FRESH), now=NOW
    )
    assert position.unrealised_pnl_vnd == -500_000
    assert position.unrealised_pnl_percent == Decimal('-7.69')


def test_zero_cost_basis_has_no_return_percentage():
    """money-rules.md: the return % is NULL when its denominator is zero."""
    position = value_position(Position('XXX', 'Zero cost', 1, 0, 5_000, FRESH), now=NOW)
    assert position.unrealised_pnl_vnd == 5_000
    assert position.unrealised_pnl_percent is None


def test_average_cost_keeps_full_precision_until_display():
    """10,000 over 3 shares has no exact integer average. The service returns
    the exact ratio; rounding is a display concern (money-rules.md)."""
    position = value_position(
        Position('ODD', 'Odd lot', 3, 10_000, 4_000, FRESH), now=NOW
    )
    assert position.average_cost_vnd == Decimal(10_000) / Decimal(3)
    assert position.cost_basis_vnd == 10_000 and position.quantity == 3


def test_valuation_never_uses_binary_floating_point():
    """Money stays int; only ratios are Decimal, so 0.1 + 0.2 problems cannot
    reach a stored or displayed figure."""
    portfolio = build_portfolio(MemoryPortfolio(), 1, now=NOW)
    position = portfolio.positions[0]
    for value in (portfolio.cash_vnd, portfolio.total_value_vnd,
                  position.market_value_vnd, position.unrealised_pnl_vnd):
        assert isinstance(value, int)
    for value in (position.average_cost_vnd, position.unrealised_pnl_percent):
        assert isinstance(value, Decimal)


def test_service_reads_only_the_account_it_is_given():
    """Ownership is an argument, never discovered inside the service. The
    session source can therefore change without affecting valuation."""
    reader = MemoryPortfolio(account_id=7)
    build_portfolio(reader, 7, now=NOW)
    assert set(reader.asked_for) == {7}

    other = build_portfolio(MemoryPortfolio(account_id=7), 8, now=NOW)
    assert other.positions == []


def test_api_payload_sends_decimals_as_strings():
    """A percentage sent as a JSON number invites a float round-trip on the
    client; the exact displayed digits travel as text instead."""
    payload = as_api_payload(build_portfolio(MemoryPortfolio(), 1, now=NOW))
    assert payload['total_value_vnd'] == 46_600_000
    assert payload['valuation_complete'] is True
    assert payload['positions'][0]['unrealised_pnl_percent'] == '10.00'
    assert payload['positions'][0]['average_cost_vnd'] == '30000'
    assert isinstance(payload['positions'][0]['market_value_vnd'], int)


def test_api_payload_marks_an_incomplete_valuation():
    unpriced = Position('SSI', 'SSI Securities', 100, 3_200_000, None, None)
    payload = as_api_payload(
        build_portfolio(MemoryPortfolio(positions=(HPG, unpriced)), 1, now=NOW)
    )
    assert payload['valuation_complete'] is False
    assert payload['unpriced_count'] == 1
    ssi = next(p for p in payload['positions'] if p['symbol'] == 'SSI')
    assert ssi['market_value_vnd'] is None and ssi['priced'] is False
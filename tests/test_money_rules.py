"""Numeric regression tests for the money rules (#51 AC3).

No trading service exists yet, so these tests encode the arithmetic defined in
`docs/money-rules.md` as reference implementations. When the buy/sell service
lands (#59 and later), its functions must reproduce every number below; swap
the local helpers for imports at that point and the expectations stay as they
are. Tests of the buy/sell *flow* itself are deferred at the bottom of the file.

Every value is integer VND. Nothing here uses binary floating point.
"""

from decimal import ROUND_HALF_UP, Decimal

import pytest

# --- Reference implementations of docs/money-rules.md ----------------------


def buy(cost_basis_vnd, quantity, price_vnd, bought):
    """Buying adds exactly price * quantity to the cost basis (money-rules.md,
    'Buying q shares at price P adds exactly P*q')."""
    return cost_basis_vnd + price_vnd * bought, quantity + bought


def average_cost(cost_basis_vnd, quantity):
    """Average cost is the ratio of the stored totals, never a separately
    stored rounded price. Returned as Decimal so the caller decides rounding."""
    if quantity == 0:
        raise ZeroDivisionError("average cost is undefined for an empty holding")
    return Decimal(cost_basis_vnd) / Decimal(quantity)


def allocate_cost(cost_basis_vnd, quantity, sold):
    """ROUND_HALF_UP(C * q / Q) as whole VND, via the exact integer form
    (2*C*q + Q) // (2*Q). A full sale allocates the whole remaining basis."""
    if not 0 < sold <= quantity:
        raise ValueError("sold quantity must be within the holding")
    if sold == quantity:
        return cost_basis_vnd
    return (2 * cost_basis_vnd * sold + quantity) // (2 * quantity)


def sell(cost_basis_vnd, quantity, price_vnd, sold):
    """Returns (proceeds, realised_pnl, remaining_cost, remaining_quantity)."""
    allocated = allocate_cost(cost_basis_vnd, quantity, sold)
    proceeds = price_vnd * sold
    return proceeds, proceeds - allocated, cost_basis_vnd - allocated, quantity - sold


def net_asset_value(cash_vnd, positions):
    """NAV = cash + market value of every holding. `positions` is an iterable
    of (quantity, market_price_vnd)."""
    return cash_vnd + sum(quantity * price for quantity, price in positions)


def display_two_decimals(value):
    """Display rounding is ROUND_HALF_UP to two places and never flows back
    into storage."""
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# --- AC3 reference numbers -------------------------------------------------


def test_cost_averaging_100_at_28k_plus_100_at_32k_is_30k():
    """#51 AC3 first number. BR6: buying more of a held symbol re-averages."""
    cost, quantity = buy(0, 0, 28_000, 100)
    assert (cost, quantity) == (2_800_000, 100)

    cost, quantity = buy(cost, quantity, 32_000, 100)
    assert (cost, quantity) == (6_000_000, 200)

    assert average_cost(cost, quantity) == Decimal(30_000)
    assert display_two_decimals(average_cost(cost, quantity)) == Decimal("30000.00")


def test_realised_gain_selling_100_at_35k_against_30k_average_is_plus_500k():
    """#51 AC3 second number. Selling 100 of the 200 shares above at 35,000
    allocates half the basis: 3,000,000 against 3,500,000 proceeds."""
    cost, quantity = 6_000_000, 200

    proceeds, realised, remaining_cost, remaining_quantity = sell(
        cost, quantity, 35_000, 100
    )

    assert proceeds == 3_500_000
    assert realised == 500_000
    assert (remaining_cost, remaining_quantity) == (3_000_000, 100)
    # The remaining average is unchanged by a sale.
    assert average_cost(remaining_cost, remaining_quantity) == Decimal(30_000)


def test_nav_200_shares_at_33k_plus_40m_cash_is_46_600_000():
    """#51 AC3 third number, matching US06-AC2 in docs/requirements.md."""
    assert net_asset_value(40_000_000, [(200, 33_000)]) == 46_600_000


# --- Supporting cases from the money-rules.md worked table -----------------


def test_full_sale_allocates_the_whole_basis_and_matches_us05():
    """money-rules.md row 1: 28,000,000 over 1,000 shares sold at 30,000."""
    proceeds, realised, remaining_cost, remaining_quantity = sell(
        28_000_000, 1_000, 30_000, 1_000
    )
    assert (proceeds, realised) == (30_000_000, 2_000_000)
    assert (remaining_cost, remaining_quantity) == (0, 0)


def test_three_partial_sales_allocate_exactly_the_acquisition_cost():
    """money-rules.md rows 2-4: 10,000 over 3 shares has no exact integer
    average, yet the three allocations still sum to exactly 10,000."""
    cost, quantity = 10_000, 3
    allocated_total = 0

    for expected_allocated, expected_cost, expected_quantity in [
        (3_333, 6_667, 2),
        (3_334, 3_333, 1),
        (3_333, 0, 0),
    ]:
        allocated = allocate_cost(cost, quantity, 1)
        assert allocated == expected_allocated
        allocated_total += allocated
        cost, quantity = cost - allocated, quantity - 1
        assert (cost, quantity) == (expected_cost, expected_quantity)

    assert allocated_total == 10_000


def test_exact_half_vnd_rounds_up():
    """money-rules.md row 3: 6,667 over 2 shares is 3,333.5 -> 3,334."""
    assert allocate_cost(6_667, 2, 1) == 3_334


def test_zero_remaining_basis_is_valid():
    """money-rules.md row 5: 1 VND over 2 shares leaves a zero-cost share."""
    allocated = allocate_cost(1, 2, 1)
    assert allocated == 1
    assert 1 - allocated == 0


def test_average_cost_is_undefined_for_an_empty_holding():
    """Return percentage is NULL when its denominator is zero, so the service
    must not divide by a zero quantity."""
    with pytest.raises(ZeroDivisionError):
        average_cost(0, 0)


def test_allocation_rejects_quantities_outside_the_holding():
    """0 < q <= Q. BR2 forbids selling more than is held."""
    for sold in (0, -1, 201):
        with pytest.raises(ValueError):
            allocate_cost(6_000_000, 200, sold)


def test_nav_of_an_empty_portfolio_is_cash_only():
    """US06-AC3: no positions means the total equals cash."""
    assert net_asset_value(100_000_000, []) == 100_000_000


def test_money_arithmetic_never_uses_binary_floating_point():
    """0.1 + 0.2 != 0.3 in binary floating point. Every helper above returns
    int or Decimal, so this class of error cannot reach storage."""
    cost, quantity = buy(0, 0, 28_000, 100)
    proceeds, realised, remaining_cost, _ = sell(cost, quantity, 35_000, 50)

    for value in (cost, quantity, proceeds, realised, remaining_cost):
        assert isinstance(value, int)
    assert isinstance(average_cost(6_000_000, 200), Decimal)


# --- Deferred: buy/sell service flow (#51 AC4) -----------------------------
#
# These are not placeholder tests. Each names a behaviour that cannot be
# tested because no service implements it yet, and states what it will assert
# once the trading service exists.

# Buy persistence, rejection, concurrency and rollback now exercise the real
# implementation in tests/test_orders.py; do not retain empty skipped duplicates.
DEFERRED = "Sell/auth integration is pending #79/#77; real buy checks are in test_orders.py."


@pytest.mark.skip(reason=DEFERRED)
def test_sell_order_is_rejected_beyond_the_held_quantity():
    """BR2 / US05-AC2: holding 500, selling 800 is refused."""


@pytest.mark.skip(reason=DEFERRED)
def test_market_order_fills_at_the_quote_when_submitted():
    """BR3 / US05-AC3: a later quote change does not alter the fill price."""


@pytest.mark.skip(reason=DEFERRED)
def test_account_creation_grants_the_initial_capital_exactly_once():
    """BR5: the grant and the account are created in one transaction, and a
    duplicate email creates neither."""

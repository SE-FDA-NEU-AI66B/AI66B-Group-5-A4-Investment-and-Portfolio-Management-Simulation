"""Pure sell rules for #79: proceeds, allocated cost, remaining holding and
realised P&L as exact integer VND.

This is the calculation boundary agreed in docs/api-contract.md section 7.1
(`calculate_sell(holding, quantity, fill_price_vnd) -> SellResult`). It contains
no Flask, SQLite or transaction code: the shared `preview_order` and
`execute_sell` own the one preview/execution path, so this module adds neither a
second preview endpoint nor its own unit of work.
"""

from dataclasses import dataclass

from virtutrade.orders.errors import OrderError

MAX_INTEGER = 9_007_199_254_740_991


@dataclass(frozen=True)
class SellResult:
    """Everything a sale changes, minus the transport-level trade envelope."""

    proceeds_vnd: int
    allocated_cost_vnd: int
    remaining_quantity: int
    remaining_cost_vnd: int
    realised_pnl_vnd: int


def allocate_cost(cost_basis_vnd, quantity, sold_quantity):
    """ROUND_HALF_UP(C * q / Q) to a whole VND via the exact integer form
    (2*C*q + Q) // (2*Q) from docs/money-rules.md. A full sale allocates the
    whole remaining basis, so allocated + remaining always equals C."""
    if sold_quantity == quantity:
        return cost_basis_vnd
    return (2 * cost_basis_vnd * sold_quantity + quantity) // (2 * quantity)


def calculate_sell(holding, quantity, fill_price_vnd, *, symbol=None):
    """Validate a sale against the held position and return its SellResult.

    The caller supplies the already-resolved holding and fill price; freshness
    and the exact preview timestamp are re-checked inside the shared
    transaction, never here.
    """
    if type(quantity) is not int or not 1 <= quantity <= MAX_INTEGER:
        raise OrderError(
            "INVALID_QUANTITY",
            "Quantity must be a whole number of at least 1 share.",
        )
    if type(fill_price_vnd) is not int or not 0 < fill_price_vnd <= MAX_INTEGER:
        raise OrderError(
            "VALIDATION_ERROR",
            "The fill price is invalid. Preview the order again.",
        )
    held = holding.quantity
    if quantity > held:
        label = f" {symbol}" if symbol else ""
        raise OrderError(
            "INSUFFICIENT_SHARES",
            f"You hold {held:,}{label}; the maximum you can sell is {held:,}."
            " Reduce the quantity and preview again.",
            {"available_quantity": held, "requested_quantity": quantity},
        )
    proceeds = fill_price_vnd * quantity
    if proceeds > MAX_INTEGER:
        raise OrderError(
            "VALIDATION_ERROR",
            "The order exceeds supported limits. Reduce the quantity.",
        )
    allocated = allocate_cost(holding.cost_basis_vnd, held, quantity)
    return SellResult(
        proceeds_vnd=proceeds,
        allocated_cost_vnd=allocated,
        remaining_quantity=held - quantity,
        remaining_cost_vnd=holding.cost_basis_vnd - allocated,
        realised_pnl_vnd=proceeds - allocated,
    )

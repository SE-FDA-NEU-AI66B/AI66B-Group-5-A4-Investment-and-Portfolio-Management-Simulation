# Money and cost allocation decision

PO design decision for #48/#49, 3 October 2026; resolves F10 from
[Tue's independent ERD review](erd-review.md). Proposed for peer approval before
trading implementation. The current skeleton does not execute trades.

## Exact storage and arithmetic

Store cash, total holding cost, fill price and realised P&L as integer VND;
store quantity as an integer share count. Average cost is the ratio
`cost_basis_vnd / quantity`, never a separately stored rounded price.
Use exact integer arithmetic for prices multiplied by quantities. When a
division is necessary, use sufficient Decimal precision and explicit rounding,
or the equivalent exact integer formula below; never binary floating point.

Display average cost and percentages to two decimals using ROUND_HALF_UP.
Display values never flow back into cash, cost basis or P&L storage. API integers
are bounded to the exact JavaScript integer range so browser previews remain
consistent; the backend checks multiplication and final balances for overflow.

## Partial and full sale allocation

Let C be the current total integer cost basis, Q the held quantity, and q the
quantity sold, with 0 < q <= Q. For a partial sale allocate:

`allocated_cost_vnd = ROUND_HALF_UP(C * q / Q)` to a whole VND.

Because all operands are nonnegative, the exact integer equivalent is
`(2 * C * q + Q) // (2 * Q)`. Do not round the average per-share cost first.
Set the remaining cost to `C - allocated_cost_vnd`; compute realised profit as
`sale_proceeds_vnd - allocated_cost_vnd`. Thus allocated + remaining always
equals C, even when a one-VND rounding residual occurs.

For a full sale allocate **all remaining C** and delete the holding. Sequential
partial sales can distribute rounding differently, but the total allocated cost
over the lifetime of a fully sold holding is exactly its acquisition cost.
This deliberate whole-VND allocation updates storage; UI display rounding does not.

| Before (cost / shares) | Sell | Allocated cost | Remaining cost / shares | Explanation |
|------------------------|------|----------------|-------------------------|-------------|
| 28,000,000 / 1,000 | 1,000 at 30,000 | 28,000,000 | no holding | Proceeds 30,000,000; realised P&L +2,000,000 |
| 10,000 / 3 | 1 | 3,333 | 6,667 / 2 | Round 3,333.333... once |
| 6,667 / 2 | 1 | 3,334 | 3,333 / 1 | Exact half VND rounds up |
| 3,333 / 1 | 1 | 3,333 | no holding | Total allocated across three sales =10,000 |
| 1 / 2 | 1 | 1 | 0 / 1 | Zero remaining basis is valid; return % is NULL when its denominator is zero |

Buying q shares at price P adds exactly P*q to cost basis and q to quantity;
the new average is the ratio of those totals. For example 100 shares costing
2,800,000 plus another 100 costing 3,200,000 gives 6,000,000/200=30,000 VND.
Cash, holdings and trade update atomically as described in the API contract.

## Initial grant and schema boundaries

Create an account and its one-time 100,000,000 VND cash grant in the same
transaction. A duplicate email must fail without a second account/grant. Login,
logout and Admin enable/disable never reinitialize cash; the DB default alone
does not implement this service behavior.

Keep one latest quote per instrument; time-series history remains deferred for
US09/US11. Login lockout/session storage identified as F1 requires a future
migration before US01 implementation. The existing six tables cover the M2
snapshot and core trade storage, not those missing services.

Reference for explicit decimal rounding: [Python decimal](https://docs.python.org/3/library/decimal.html#decimal.ROUND_HALF_UP).

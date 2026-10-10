"""Exact-money preview and buy rules, independent of Flask and SQLite."""

import re
from datetime import datetime, timezone

from virtutrade.market.service import parse_timestamp
from virtutrade.orders.errors import OrderError

MAX_INTEGER = 9_007_199_254_740_991


def validate_order(side, symbol, quantity):
    if side not in ("buy", "sell") or not isinstance(symbol, str):
        raise OrderError(
            "VALIDATION_ERROR", "Choose buy or sell and a valid stock symbol."
        )
    symbol = symbol.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]{2,9}", symbol):
        raise OrderError(
            "TICKER_NOT_FOUND", "Ticker not found. Choose a stock from Market."
        )
    if type(quantity) is not int or not 1 <= quantity <= MAX_INTEGER:
        raise OrderError(
            "INVALID_QUANTITY", "Quantity must be a whole number of at least 1 share."
        )
    return symbol


def load_inputs(repo, session_id, symbol, now):
    account = repo.account_for_session(session_id)
    try:
        valid = (
            account
            and account.revoked_at is None
            and parse_timestamp(account.expires_at) > now
        )
    except (TypeError, ValueError, AttributeError):
        valid = False
    if not valid:
        raise OrderError(
            "AUTH_REQUIRED", "Your session has ended. Sign in again before trading."
        )
    if account.status != "active":
        raise OrderError(
            "ACCOUNT_DISABLED", "Trading is disabled for this account. Contact support."
        )
    quote = repo.quote(symbol)
    if quote is None:
        raise OrderError(
            "TICKER_NOT_FOUND", "Ticker not found. Choose a stock from Market."
        )
    if type(quote.price_vnd) is not int or not 0 < quote.price_vnd <= MAX_INTEGER:
        raise OrderError(
            "QUOTE_UNAVAILABLE",
            "No valid price is available. Return to Market and try again later.",
        )
    try:
        age = (now - parse_timestamp(quote.quoted_at)).total_seconds()
        fresh = -300 <= age <= 900
    except (TypeError, ValueError, AttributeError):
        fresh = False
    if not fresh:
        advice = (
            "Generate demo quotes, then preview again."
            if quote.source == "simulation"
            else "Wait for a fresh market quote, then preview again."
        )
        raise OrderError("QUOTE_STALE", "Price may be delayed. " + advice)
    return account, quote, repo.holding(account.id, quote.instrument_id)


def checked(value):
    if not 0 <= value <= MAX_INTEGER:
        raise OrderError(
            "VALIDATION_ERROR",
            "The order exceeds supported limits. Reduce the quantity.",
        )
    return value


def preview_order(session_id, side, symbol, quantity, unit_of_work, *, now=None):
    now = now or datetime.now(timezone.utc)
    symbol = validate_order(side, symbol, quantity)
    with unit_of_work(write=False) as repo:
        account, quote, holding = load_inputs(repo, session_id, symbol, now)
        cost = checked(quote.price_vnd * quantity)
        shortfall = max(0, cost - account.cash_vnd) if side == "buy" else 0
        allowed = shortfall == 0 if side == "buy" else quantity <= holding.quantity
        warning = None
        if shortfall:
            warning = (
                f"Exceeds available balance by {shortfall:,} VND. Reduce the quantity."
            )
        elif not allowed:
            warning = f"You hold {holding.quantity:,} {symbol}; the maximum you can sell is {holding.quantity:,}."
        return {
            "side": side,
            "symbol": symbol,
            "quantity": quantity,
            "estimate_vnd": cost,
            "cash_vnd": account.cash_vnd,
            "available_quantity": holding.quantity,
            "shortfall_vnd": shortfall,
            "can_submit": allowed,
            "warning": warning,
            "quote": {
                "price_vnd": quote.price_vnd,
                "quoted_at": quote.quoted_at,
                "source": quote.source,
            },
        }


def execute_buy(
    session_id, symbol, quantity, expected_quote_at, unit_of_work, *, now=None
):
    now = now or datetime.now(timezone.utc)
    symbol = validate_order("buy", symbol, quantity)
    if not isinstance(expected_quote_at, str) or not expected_quote_at:
        raise OrderError("VALIDATION_ERROR", "Preview the order before confirming it.")
    with unit_of_work(write=True) as repo:
        account, quote, holding = load_inputs(repo, session_id, symbol, now)
        if quote.quoted_at != expected_quote_at:
            raise OrderError(
                "QUOTE_CHANGED", "Price changed; refresh the preview before confirming."
            )
        cost = checked(quote.price_vnd * quantity)
        if cost > account.cash_vnd:
            raise OrderError(
                "INSUFFICIENT_CASH",
                f"Insufficient cash: this order needs {cost:,} VND but only "
                f"{account.cash_vnd:,} VND is available. Reduce the quantity and preview again.",
                {"required_vnd": cost, "available_vnd": account.cash_vnd},
            )
        new_quantity = checked(holding.quantity + quantity)
        new_cost = checked(holding.cost_basis_vnd + cost)
        stamp = now.isoformat().replace("+00:00", "Z")
        trade_id = repo.save_buy(account, quote, holding, quantity, cost, stamp)
        return {
            "trade": {
                "id": trade_id,
                "symbol": symbol,
                "side": "buy",
                "quantity": quantity,
                "fill_price_vnd": quote.price_vnd,
                "executed_at": stamp,
                "realised_pnl_vnd": None,
            },
            "cash_vnd": account.cash_vnd - cost,
            "holding": {
                "symbol": symbol,
                "quantity": new_quantity,
                "cost_basis_vnd": new_cost,
            },
        }

"""Immutable stored inputs to the order rules."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Account:
    id: int
    cash_vnd: int
    status: str
    expires_at: str
    revoked_at: str | None


@dataclass(frozen=True)
class OrderQuote:
    instrument_id: int
    symbol: str
    price_vnd: int
    quoted_at: str
    source: str


@dataclass(frozen=True)
class Holding:
    quantity: int = 0
    cost_basis_vnd: int = 0

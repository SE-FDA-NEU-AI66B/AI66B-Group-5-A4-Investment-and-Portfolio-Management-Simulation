"""Immutable domain values for the accounts module."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Account:
    id: int
    email: str
    role: str
    cash_vnd: int


@dataclass(frozen=True)
class SessionRecord:
    id: int
    account_id: int
    created_at: str
    expires_at: str
    last_seen_at: str

"""Compatibility imports for existing tests and the separately reviewed DNSE draft.

New application code imports virtutrade.database or market.repository directly.
"""

from virtutrade.database import SCHEMA, init_database
from virtutrade.market.repository import MARKET_QUERY, read_market

__all__ = ['MARKET_QUERY', 'SCHEMA', 'init_database', 'read_market']

"""Storage-independent failures the market controller can translate to HTTP."""


class MarketDataUnavailable(Exception):
    """The stored market snapshot could not be read."""

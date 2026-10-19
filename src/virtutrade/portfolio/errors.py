"""Storage-independent failures the portfolio controller can translate to HTTP."""


class PortfolioDataUnavailable(Exception):
    """The stored portfolio could not be read."""


class AccountNotFound(Exception):
    """The session names an account that does not exist in storage."""
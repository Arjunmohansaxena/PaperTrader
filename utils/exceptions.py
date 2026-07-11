class InsufficientFundsError(Exception):
    """Raised when a user does not have enough cash for a trade."""


class InsufficientSharesError(Exception):
    """Raised when a user tries to sell more shares than they own."""


class StockNotFoundError(Exception):
    """Raised when a requested stock cannot be found in the market data source."""


class UserAlreadyExistsError(Exception):
    """Raised when attempting to create a user that already exists."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid."""

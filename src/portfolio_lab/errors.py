"""Domain-specific errors for portfolio lab."""


class PortfolioLabError(Exception):
    """Base error class."""


class ValidationError(PortfolioLabError):
    """Input validation error."""


class DuplicateAssetError(ValidationError):
    """Raised when registering duplicate asset identifier."""


class SnapshotError(PortfolioLabError):
    """Snapshot workflow error."""


class MissingDataError(PortfolioLabError):
    """Raised when required market data is missing."""


class NetworkAccessError(PortfolioLabError):
    """Raised when outbound network access is attempted during backtest."""

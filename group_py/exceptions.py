"""Custom exceptions for GroupMe bot package."""


class GroupMeBotError(Exception):
    """Base exception for all bot errors."""

    pass


class ConfigurationError(GroupMeBotError):
    """Raised when bot is misconfigured (missing credentials, etc.)."""

    pass


class APIError(GroupMeBotError):
    """Raised when GroupMe API returns an error."""

    pass

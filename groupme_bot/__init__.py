"""GroupMe bot framework with command routing and storage."""

from .bot import GroupMeBot
from .sender import GroupMeSender
from .models import Message
from .exceptions import GroupMeBotError, ConfigurationError, APIError

__version__ = "2.0.0"
__all__ = [
    "GroupMeBot",
    "GroupMeSender",
    "Message",
    "GroupMeBotError",
    "ConfigurationError",
    "APIError",
]

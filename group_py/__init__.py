"""GroupMe bot framework with command routing, real-time support, and flexible message handling."""

from .bot import GroupMeBotManager
from .sender import GroupMeBot
from .models import Message
from .exceptions import GroupMeBotError, ConfigurationError, APIError

__version__ = "3.0.0"
__all__ = [
    "GroupMeBotManager",
    "GroupMeBot",
    "Message",
    "GroupMeBotError",
    "ConfigurationError",
    "APIError",
]

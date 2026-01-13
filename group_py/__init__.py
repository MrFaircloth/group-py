"""GroupMe bot framework with command routing, real-time support, and flexible message handling."""

from .bot import GroupMeBotManager
from .client import GroupMeClient
from .sender import GroupMeBot
from .models import Message
from .exceptions import GroupMeBotError, ConfigurationError, APIError

__version__ = "3.0.0"
__all__ = [
    "GroupMeBotManager",
    "GroupMeClient",
    "GroupMeBot",
    "Message",
    "GroupMeBotError",
    "ConfigurationError",
    "APIError",
]

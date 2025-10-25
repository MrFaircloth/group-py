from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .router import MessageRouter
    from .groupme_message import Message
    from group_py.api.bots import GroupMeBot


@dataclass
class HandlerContext:
    """
    Context object passed to message handlers containing all necessary dependencies.
    
    This provides a clean way to pass bot and router references to handlers without
    creating circular imports or tight coupling.
    """
    bot: 'GroupMeBot'
    router: 'MessageRouter'
    message: 'Message'


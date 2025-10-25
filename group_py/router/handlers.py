from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .groupme_message import Message

if TYPE_CHECKING:
    from .context import HandlerContext


class MessageHandler(ABC):
    '''Abstract message handler class.'''

    @staticmethod
    @abstractmethod
    def can_handle(message: Message) -> bool:
        '''
        Checks message contents for handler criteria.
        Example: `return message.text.lower().strip() == '!ready'`
        '''

    @staticmethod
    @abstractmethod
    def execute(context: 'HandlerContext') -> None:
        '''Executes action based on given input. Receives HandlerContext with bot, router, and message.'''


class CommandHandler(MessageHandler):
    '''Base class for command-based message handlers.'''

    command_str: str = ''
    '''Override this in subclasses with the command string (e.g., '!help')'''

    @classmethod
    def command(cls) -> str:
        '''
        String which will be used to call for execute.
        E.G. `!command`
        '''
        return cls.command_str

    @classmethod
    def can_handle(cls, message: Message) -> bool:
        '''
        Default implementation checks if message matches the command string.
        Subclasses can override for custom matching logic.
        '''
        return message.text.lower().strip() == cls.command_str

    @staticmethod
    def help() -> str:
        '''
        Returns instructions on how to use the command.
        '''
        return ''

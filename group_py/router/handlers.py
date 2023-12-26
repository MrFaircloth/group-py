from abc import ABC, abstractmethod

from .groupme_message import Message


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
    def execute(message: Message) -> None:
        '''Executes action based on given input.'''


class CommandHandler(MessageHandler):
    @property
    @staticmethod
    def command() -> str:
        '''
        String which will be used to call for execute.
        E.G. `!command`
        '''
        return ''

    @staticmethod
    def help() -> str:
        '''
        Returns instructions on how to use the comand.
        TODO: Move to own inheriting class. Maybe CommandHandler ?
        '''
        return ''

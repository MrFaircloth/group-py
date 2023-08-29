import pytest
from unittest.mock import Mock

from group_py.callback_handler import MessageRouter, MessageHandler, Message


class ReadyHandler(MessageHandler):
    def can_handle(message: Message) -> bool:
        '''
        Checks message contents for handler criteria.
        '''
        return message.text.lower().strip() == '!ready'

    def execute(message: Message) -> None:
        '''Executes action based on given input.'''
        pass


def test_router():
    router = MessageRouter([ReadyHandler])
    ready_route = router.get_route_by_name(ReadyHandler.__name__)

    message = Mock()
    message.text = 'Hello World!'

    router.route(message)
    assert ready_route.executions == 0

    message.text = '!ready'
    router.route(message)
    assert ready_route.executions == 1

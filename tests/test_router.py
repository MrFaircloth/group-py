import pytest
from unittest.mock import Mock, patch

from group_py.router import MessageRouter, CommandHandler, Message
from group_py.router.help import HelpHandler


class ReadyHandler(CommandHandler):
    @staticmethod
    def command():
        return '!ready'

    @staticmethod
    def help():
        return 'Responds when users are ready.'

    @staticmethod
    def can_handle(message: Message) -> bool:
        '''
        Checks message contents for handler criteria.
        '''
        return message.text.lower().strip() == '!ready'

    @staticmethod
    def execute(message: Message) -> None:
        '''
        Executes action based on given input.
        '''
        pass


def test_router_help():
    """Test that help command generates expected help output without posting a message."""
    # Mock the GroupMeBot to capture the help message without posting
    with patch('group_py.router.help.GroupMeBot') as mock_bot_class:
        mock_bot_instance = Mock()
        mock_bot_class.return_value = mock_bot_instance

        # Create router with ReadyHandler
        router = MessageRouter([ReadyHandler])

        # Create help message
        message = Mock()
        message.text = '!help'

        # Route the help message
        router.route(message)

        # Verify bot was instantiated and post_message was called
        mock_bot_class.assert_called_once()
        mock_bot_instance.post_message.assert_called_once()

        # Get the help message that would have been posted
        posted_message = mock_bot_instance.post_message.call_args[0][0]

        # Validate the help content includes the HelpHandler's own help
        assert '!help' in posted_message
        assert 'Collects all commands and prints functionality.' in posted_message

        # Validate the help content includes the ReadyHandler
        assert '!ready' in posted_message
        assert 'Responds when users are ready.' in posted_message
    




def test_router_custom_handler():
    router = MessageRouter([ReadyHandler])
    ready_route = router.get_route_by_name(ReadyHandler.__name__)

    message = Mock()
    message.text = 'Hello World!'

    router.route(message)
    assert ready_route.executions == 0

    message.text = '!ready'
    router.route(message)
    assert ready_route.executions == 1

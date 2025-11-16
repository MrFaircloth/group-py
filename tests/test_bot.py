"""Tests for GroupMeBot."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from groupme_bot import GroupMeBot, Message


@pytest.fixture
def mock_bot(mock_api_key, mock_bot_id, mock_group_id):
    """Create a bot with mocked API calls."""
    with patch("groupme_bot.bot.GroupMeClient") as mock_client:
        bot = GroupMeBot(
            api_key=mock_api_key, bot_id=mock_bot_id, group_id=mock_group_id, auto_create=False
        )
        bot.client = mock_client.return_value
        yield bot


def test_bot_initialization(mock_api_key, mock_bot_id, mock_group_id):
    """Test bot initialization."""
    with patch("groupme_bot.bot.GroupMeClient"):
        bot = GroupMeBot(
            api_key=mock_api_key, bot_id=mock_bot_id, group_id=mock_group_id, auto_create=False
        )

        assert bot.api_key == mock_api_key
        assert bot.bot_id == mock_bot_id
        assert bot.group_id == mock_group_id


def test_bot_initialization_from_env():
    """Test bot initialization from environment variables."""
    with patch.dict(
        "os.environ",
        {
            "GROUPME_API_KEY": "env_api_key",
            "GROUPME_BOT_ID": "env_bot_id",
            "GROUPME_GROUP_ID": "env_group_id",
        },
    ):
        with patch("groupme_bot.bot.GroupMeClient"):
            bot = GroupMeBot(auto_create=False)

            assert bot.api_key == "env_api_key"
            assert bot.bot_id == "env_bot_id"
            assert bot.group_id == "env_group_id"


def test_command_decorator(mock_bot):
    """Test @command decorator."""
    handler_called = False
    received_args = None

    @mock_bot.command("/test")
    def test_handler(message, args):
        nonlocal handler_called, received_args
        handler_called = True
        received_args = args

    # Process a command message
    data = {
        "id": "msg_1",
        "text": "/test hello world",
        "user_id": "user_1",
        "group_id": "group_1",
        "created_at": 1234567890,
        "sender_type": "user",
    }

    mock_bot.process_message(data)

    assert handler_called
    assert received_args == "hello world"


def test_on_message_decorator(mock_bot):
    """Test @on_message decorator."""
    handler_called = False

    @mock_bot.on_message
    def test_handler(message):
        nonlocal handler_called
        handler_called = True

    # Process a regular message
    data = {
        "id": "msg_1",
        "text": "hello",
        "user_id": "user_1",
        "group_id": "group_1",
        "created_at": 1234567890,
        "sender_type": "user",
    }

    mock_bot.process_message(data)

    assert handler_called


def test_on_unknown_command_decorator(mock_bot):
    """Test @on_unknown_command decorator."""
    handler_called = False
    received_command = None

    @mock_bot.on_unknown_command
    def test_handler(message, command_text):
        nonlocal handler_called, received_command
        handler_called = True
        received_command = command_text

    # Process an unknown command
    data = {
        "id": "msg_1",
        "text": "/unknown test",
        "user_id": "user_1",
        "group_id": "group_1",
        "created_at": 1234567890,
        "sender_type": "user",
    }

    mock_bot.process_message(data)

    assert handler_called
    assert received_command == "/unknown test"


def test_ignore_bot_messages(mock_bot):
    """Test that bot ignores its own messages."""
    handler_called = False

    @mock_bot.on_message
    def test_handler(message):
        nonlocal handler_called
        handler_called = True

    # Process a bot message
    data = {
        "id": "msg_1",
        "text": "hello",
        "user_id": "bot_1",
        "group_id": "group_1",
        "created_at": 1234567890,
        "sender_type": "bot",
    }

    mock_bot.process_message(data)

    assert not handler_called


def test_send_message(mock_bot):
    """Test send_message method."""
    mock_bot.client.send_message = Mock()

    mock_bot.send_message("Hello, world!")

    mock_bot.client.send_message.assert_called_once_with(
        mock_bot.bot_id, "Hello, world!", image_url=None, attachments=None
    )

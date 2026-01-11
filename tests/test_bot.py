"""Tests for GroupMeBotManager."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from group_py import GroupMeBotManager, Message


@pytest.fixture
def mock_manager(mock_api_key, mock_bot_id, mock_group_id):
    """Create a manager with mocked API calls."""
    with patch("group_py.bot.GroupMeClient") as mock_client:
        manager = GroupMeBotManager(
            api_key=mock_api_key,
            bot_id=mock_bot_id,
            group_id=mock_group_id,
            callback_url="https://test.com/webhook",
        )
        manager.client = mock_client.return_value
        yield manager


def test_manager_initialization(mock_api_key, mock_bot_id, mock_group_id):
    """Test manager initialization."""
    with patch("group_py.bot.GroupMeClient"):
        manager = GroupMeBotManager(
            api_key=mock_api_key,
            bot_id=mock_bot_id,
            group_id=mock_group_id,
            callback_url="https://test.com/webhook",
        )

        assert manager.api_key == mock_api_key
        assert manager.primary_bot.bot_id == mock_bot_id
        assert manager.group_id == mock_group_id


def test_manager_initialization_from_env():
    """Test manager initialization from environment variables."""
    with patch.dict(
        "os.environ",
        {
            "GROUPME_API_KEY": "env_api_key",
            "GROUPME_BOT_ID": "env_bot_id",
            "GROUPME_GROUP_ID": "env_group_id",
            "GROUPME_CALLBACK_URL": "https://test.com/webhook",
        },
    ):
        with patch("group_py.bot.GroupMeClient"):
            manager = GroupMeBotManager()

            assert manager.api_key == "env_api_key"
            assert manager.primary_bot.bot_id == "env_bot_id"
            assert manager.group_id == "env_group_id"


def test_command_decorator(mock_manager):
    """Test @command decorator."""
    handler_called = False
    received_args = None

    @mock_manager.command("/test")
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

    mock_manager.process_webhook(data)

    assert handler_called
    assert received_args == "hello world"


def test_on_message_decorator(mock_manager):
    """Test @on_message decorator."""
    handler_called = False

    @mock_manager.on_message
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

    mock_manager.process_webhook(data)

    assert handler_called


def test_on_unknown_command_decorator(mock_manager):
    """Test @on_unknown_command decorator."""
    handler_called = False
    received_command = None

    @mock_manager.on_unknown_command
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

    mock_manager.process_webhook(data)

    assert handler_called
    assert received_command == "/unknown test"


def test_ignore_bot_messages(mock_manager):
    """Test that manager ignores bot messages."""
    handler_called = False

    @mock_manager.on_message
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

    mock_manager.process_webhook(data)

    assert not handler_called


def test_bot_send_message(mock_manager):
    """Test bot send_message method."""
    mock_manager.client.send_message = Mock()

    # Get primary bot and send message
    bot = mock_manager.primary_bot
    bot.send_message("Hello, world!")

    mock_manager.client.send_message.assert_called_once_with(
        "Hello, world!", image_url=None, mentions=None
    )


def test_bot_recovery_finds_existing(mock_api_key, mock_group_id):
    """Test that bot recovery finds and reuses existing bots."""
    with patch("group_py.bot.GroupMeClient") as mock_client_class:
        mock_client = mock_client_class.return_value

        # Simulate finding an existing bot
        mock_client.find_bot.return_value = {
            "bot_id": "recovered_bot_123",
            "name": "TestBot",
            "group_id": mock_group_id,
        }

        manager = GroupMeBotManager(
            api_key=mock_api_key,
            group_id=mock_group_id,
            callback_url="https://test.com/webhook",
            bot_name="TestBot",
            # No bot_id provided - should trigger auto-create/recovery
        )

        # Should have called find_bot to check for existing
        mock_client.find_bot.assert_called_once_with("TestBot", mock_group_id)

        # Should NOT have called create_bot since we found an existing one
        mock_client.create_bot.assert_not_called()

        # Should be using the recovered bot ID
        assert manager.primary_bot.bot_id == "recovered_bot_123"


def test_bot_recovery_creates_when_not_found(mock_api_key, mock_group_id):
    """Test that a new bot is created when no existing bot is found."""
    with patch("group_py.bot.GroupMeClient") as mock_client_class:
        mock_client = mock_client_class.return_value

        # Simulate no existing bot found
        mock_client.find_bot.return_value = None

        # Simulate successful bot creation
        mock_client.create_bot.return_value = {
            "response": {
                "bot": {
                    "bot_id": "new_bot_456",
                    "name": "NewBot",
                }
            }
        }

        manager = GroupMeBotManager(
            api_key=mock_api_key,
            group_id=mock_group_id,
            callback_url="https://test.com/webhook",
            bot_name="NewBot",
        )

        # Should have checked for existing bot first
        mock_client.find_bot.assert_called_once_with("NewBot", mock_group_id)

        # Should have created a new bot since none was found
        mock_client.create_bot.assert_called_once()

        # Should be using the newly created bot ID
        assert manager.primary_bot.bot_id == "new_bot_456"

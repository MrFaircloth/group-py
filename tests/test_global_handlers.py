"""Tests for global message handlers (@on_any_message)."""

import pytest
from unittest.mock import Mock, patch
from group_py.bot import GroupMeBotManager


@pytest.fixture
def mock_manager(mock_api_key, mock_group_id, mock_bot_id):
    """Create a GroupMeBotManager instance with mocked bot creation."""
    with patch("group_py.client.GroupMeClient.create_bot"):
        manager = GroupMeBotManager(
            api_key=mock_api_key,
            group_id=mock_group_id,
            bot_id=mock_bot_id,
        )
        return manager


@pytest.fixture
def sample_webhook_data():
    """Sample webhook data for testing."""
    return {
        "id": "msg_123456",
        "text": "Hello, world!",
        "user_id": "user_123",
        "name": "Test User",
        "group_id": "group_123",
        "created_at": 1234567890,
        "system": False,
        "sender_type": "user",
        "avatar_url": "https://example.com/avatar.jpg",
        "attachments": [],
    }


class TestOnAnyMessage:
    """Test @on_any_message decorator."""

    def test_on_any_message_fires_for_all(self, mock_manager, sample_webhook_data):
        """Test that @on_any_message handler fires for all messages."""
        # Track calls
        call_log = []

        @mock_manager.on_any_message
        def logger(message):
            call_log.append(("logger", message.text))

        # Process a normal message
        mock_manager.process_webhook(sample_webhook_data)

        assert len(call_log) == 1
        assert call_log[0] == ("logger", "Hello, world!")

    def test_on_any_message_fires_before_commands(self, mock_manager, sample_webhook_data):
        """Test that @on_any_message fires before command routing."""
        # Track execution order
        call_order = []

        @mock_manager.on_any_message
        def preprocessor(message):
            call_order.append("preprocessor")

        @mock_manager.command("/test")
        def test_command(message, args):
            call_order.append("command")

        # Process a command message
        command_data = sample_webhook_data.copy()
        command_data["text"] = "/test hello"
        mock_manager.process_webhook(command_data)

        # Preprocessor should run first
        assert call_order == ["preprocessor", "command"]

    def test_multiple_preprocessors(self, mock_manager, sample_webhook_data):
        """Test that multiple preprocessors execute in order."""
        call_order = []

        @mock_manager.on_any_message
        def first(message):
            call_order.append("first")

        @mock_manager.on_any_message
        def second(message):
            call_order.append("second")

        @mock_manager.on_any_message
        def third(message):
            call_order.append("third")

        mock_manager.process_webhook(sample_webhook_data)

        # All three should execute in registration order
        assert call_order == ["first", "second", "third"]

    def test_preprocessor_exception_doesnt_break_routing(self, mock_manager, sample_webhook_data):
        """Test that exception in preprocessor doesn't break message routing."""
        call_log = []

        @mock_manager.on_any_message
        def failing_preprocessor(message):
            call_log.append("failing")
            raise Exception("Preprocessor error!")

        @mock_manager.on_any_message
        def working_preprocessor(message):
            call_log.append("working")

        @mock_manager.command("/test")
        def test_command(message, args):
            call_log.append("command")

        # Process command - should work despite failing preprocessor
        command_data = sample_webhook_data.copy()
        command_data["text"] = "/test hello"
        mock_manager.process_webhook(command_data)

        # All should execute (failing preprocessor raises exception but continues)
        assert "failing" in call_log
        assert "working" in call_log
        assert "command" in call_log

    def test_preprocessor_can_modify_message(self, mock_manager, sample_webhook_data):
        """Test that preprocessor can modify message attributes."""
        # Track what the command sees
        seen_custom_attr = None

        @mock_manager.on_any_message
        def modifier(message):
            # Add a custom attribute to the message
            message.custom_attr = "preprocessor_was_here"

        @mock_manager.command("/test")
        def test_command(message, args):
            nonlocal seen_custom_attr
            seen_custom_attr = getattr(message, "custom_attr", None)

        # Process command
        command_data = sample_webhook_data.copy()
        command_data["text"] = "/test hello"
        mock_manager.process_webhook(command_data)

        # Command should see the attribute added by preprocessor
        assert seen_custom_attr == "preprocessor_was_here"

    def test_preprocessor_fires_for_commands_and_normal_messages(self, mock_manager, sample_webhook_data):
        """Test that preprocessor runs for both commands and normal messages."""
        messages_seen = []

        @mock_manager.on_any_message
        def logger(message):
            messages_seen.append(message.text)

        @mock_manager.command("/cmd")
        def command_handler(message, args):
            pass

        # Process normal message (will trigger handlers but that's ok)
        mock_manager.process_webhook(sample_webhook_data)

        # Process command message
        command_data = sample_webhook_data.copy()
        command_data["text"] = "/cmd test"
        mock_manager.process_webhook(command_data)

        # Preprocessor should have seen both
        assert len(messages_seen) == 2
        assert messages_seen[0] == "Hello, world!"
        assert messages_seen[1] == "/cmd test"

    def test_preprocessor_skips_bot_messages(self, mock_manager, sample_webhook_data):
        """Test that preprocessor doesn't run for bot's own messages."""
        call_log = []

        @mock_manager.on_any_message
        def logger(message):
            call_log.append(message.sender_type)

        # Process bot message
        bot_data = sample_webhook_data.copy()
        bot_data["sender_type"] = "bot"
        mock_manager.process_webhook(bot_data)

        # Preprocessor should not have run (bots are skipped before preprocessors)
        assert len(call_log) == 0

    def test_preprocessor_with_no_text(self, mock_manager):
        """Test that preprocessor runs even for messages with no text."""
        call_log = []

        @mock_manager.on_any_message
        def logger(message):
            call_log.append(("message", message.text))

        # Message with no text but with attachments
        data = {
            "id": "msg_123",
            "text": None,
            "user_id": "user_123",
            "name": "Test",
            "group_id": "group_123",
            "created_at": 1234567890,
            "system": False,
            "sender_type": "user",
            "attachments": [{"type": "image", "url": "https://example.com/image.jpg"}],
        }

        mock_manager.process_webhook(data)

        # Preprocessor should still run
        assert len(call_log) == 1
        assert call_log[0] == ("message", None)

    def test_on_any_message_returns_function(self, mock_manager):
        """Test that decorator returns the original function."""
        def my_handler(message):
            pass

        result = mock_manager.on_any_message(my_handler)

        # Should return the same function (for chaining)
        assert result is my_handler

    def test_preprocessor_access_to_message_attributes(self, mock_manager, sample_webhook_data):
        """Test that preprocessor has access to all message attributes."""
        captured_attrs = {}

        @mock_manager.on_any_message
        def capture_attrs(message):
            captured_attrs["id"] = message.id
            captured_attrs["name"] = message.name
            captured_attrs["user_id"] = message.user_id
            captured_attrs["group_id"] = message.group_id

        mock_manager.process_webhook(sample_webhook_data)

        assert captured_attrs["id"] == "msg_123456"
        assert captured_attrs["name"] == "Test User"
        assert captured_attrs["user_id"] == "user_123"
        assert captured_attrs["group_id"] == "group_123"

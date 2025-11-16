"""Tests for GroupMeSender."""

import pytest
from unittest.mock import Mock, patch
from groupme_bot import GroupMeSender


@pytest.fixture
def sender(mock_api_key, mock_bot_id):
    """Create a GroupMeSender instance."""
    with patch("groupme_bot.sender.GroupMeClient"):
        return GroupMeSender(bot_id=mock_bot_id, api_key=mock_api_key)


def test_sender_initialization(mock_api_key, mock_bot_id):
    """Test sender initialization."""
    with patch("groupme_bot.sender.GroupMeClient"):
        sender = GroupMeSender(bot_id=mock_bot_id, api_key=mock_api_key)

        assert sender.bot_id == mock_bot_id
        assert sender.api_key == mock_api_key


def test_sender_send_message(sender):
    """Test send_message method."""
    sender.client = Mock()

    sender.send_message("Hello, world!")

    sender.client.send_message.assert_called_once_with(
        sender.bot_id, "Hello, world!", image_url=None, attachments=None
    )


def test_sender_send_message_with_image(sender):
    """Test send_message with image."""
    sender.client = Mock()

    sender.send_message("Check this!", image_url="https://example.com/image.jpg")

    sender.client.send_message.assert_called_once_with(
        sender.bot_id, "Check this!", image_url="https://example.com/image.jpg", attachments=None
    )


def test_sender_send_location(sender):
    """Test send_location method."""
    sender.client = Mock()

    sender.send_location("Office", 37.7749, -122.4194, text="Meet here!")

    sender.client.send_location.assert_called_once_with(
        sender.bot_id, name="Office", lat=37.7749, lng=-122.4194, text="Meet here!"
    )


def test_sender_from_env():
    """Test sender initialization from environment variables."""
    with patch.dict(
        "os.environ", {"GROUPME_API_KEY": "env_api_key", "GROUPME_BOT_ID": "env_bot_id"}
    ):
        with patch("groupme_bot.sender.GroupMeClient"):
            sender = GroupMeSender()

            assert sender.api_key == "env_api_key"
            assert sender.bot_id == "env_bot_id"

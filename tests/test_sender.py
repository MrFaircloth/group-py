"""Tests for GroupMeBot (sender)."""

import pytest
from unittest.mock import Mock, patch
from group_py import GroupMeBot
from group_py.client import GroupMeClient


@pytest.fixture
def mock_client():
    """Create a mock GroupMeClient."""
    client = Mock(spec=GroupMeClient)
    client.bot_id = "test_bot_id"
    return client


@pytest.fixture
def bot(mock_client, mock_bot_id, mock_group_id):
    """Create a GroupMeBot instance."""
    return GroupMeBot(
        bot_id=mock_bot_id,
        name="Test Bot",
        client=mock_client,
        group_id=mock_group_id,
    )


def test_bot_initialization(mock_client, mock_bot_id, mock_group_id):
    """Test bot initialization."""
    bot = GroupMeBot(
        bot_id=mock_bot_id,
        name="Test Bot",
        client=mock_client,
        group_id=mock_group_id,
    )

    assert bot.bot_id == mock_bot_id
    assert bot.name == "Test Bot"
    assert bot.client == mock_client
    assert bot.group_id == mock_group_id


def test_bot_send_message(bot, mock_client):
    """Test send_message method."""
    mock_client.send_message = Mock(return_value={"id": "msg_1"})

    bot.send_message("Hello, world!")

    # Should swap bot_id temporarily and pass mentions parameter
    mock_client.send_message.assert_called_once_with("Hello, world!", image_url=None, mentions=None)


def test_bot_send_message_with_image(bot, mock_client):
    """Test send_message with image."""
    mock_client.send_message = Mock(return_value={"id": "msg_1"})

    bot.send_message("Check this!", image_url="https://example.com/image.jpg")

    mock_client.send_message.assert_called_once_with(
        "Check this!", image_url="https://example.com/image.jpg", mentions=None
    )


def test_bot_send_location(bot, mock_client):
    """Test send_location method."""
    mock_client.send_location = Mock(return_value={"id": "msg_1"})

    bot.send_location("Office", 37.7749, -122.4194, text="Meet here!")

    # send_location passes args positionally
    mock_client.send_location.assert_called_once_with(
        "Office", 37.7749, -122.4194, "Meet here!"
    )


def test_bot_send_message_with_mentions(mock_client, mock_bot_id, mock_group_id):
    """Test send_message with mentions."""
    bot = GroupMeBot(
        bot_id=mock_bot_id,
        name="Test Bot",
        client=mock_client,
        group_id=mock_group_id,
    )

    mock_client.send_message = Mock(return_value={"id": "msg_1"})
    mentions = [{"user_id": "123", "name": "Bob"}]

    bot.send_message("Hello @Bob!", mentions=mentions)

    # Should pass mentions to client
    mock_client.send_message.assert_called_once_with(
        "Hello @Bob!", image_url=None, mentions=mentions
    )

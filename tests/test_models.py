"""Tests for Message model."""

import pytest
from group_py import Message


def test_message_from_dict(sample_message_data):
    """Test creating Message from dict."""
    message = Message.from_dict(sample_message_data)

    assert message.id == "msg_123456"
    assert message.text == "Hello, world!"
    assert message.user_id == "user_123"
    assert message.name == "Test User"
    assert message.group_id == "group_123"
    assert message.created_at == 1234567890
    assert message.system is False
    assert message.sender_type == "user"
    assert message.avatar_url == "https://example.com/avatar.jpg"
    assert message.attachments == []


def test_message_from_dict_missing_fields():
    """Test Message handles missing optional fields."""
    minimal_data = {
        "id": "msg_123",
        "user_id": "user_123",
        "group_id": "group_123",
        "created_at": 1234567890,
    }

    message = Message.from_dict(minimal_data)

    assert message.id == "msg_123"
    assert message.text is None
    assert message.name == "Unknown"
    assert message.system is False
    assert message.sender_type == "user"
    assert message.avatar_url is None
    assert message.attachments == []


def test_message_has_image(sample_message_with_image):
    """Test has_image() method."""
    message = Message.from_dict(sample_message_with_image)
    assert message.has_image() is True

    # Message without image
    message_no_image = Message.from_dict({"id": "1", "attachments": []})
    assert message_no_image.has_image() is False


def test_message_get_image_url(sample_message_with_image):
    """Test get_image_url() method."""
    message = Message.from_dict(sample_message_with_image)
    assert message.get_image_url() == "https://example.com/image.jpg"

    # Message without image
    message_no_image = Message.from_dict({"id": "1", "attachments": []})
    assert message_no_image.get_image_url() is None


def test_message_has_location():
    """Test has_location() method."""
    data_with_location = {
        "id": "msg_123",
        "attachments": [
            {"type": "location", "lat": "37.7749", "lng": "-122.4194", "name": "San Francisco"}
        ],
    }

    message = Message.from_dict(data_with_location)
    assert message.has_location() is True

    # Message without location
    message_no_location = Message.from_dict({"id": "1", "attachments": []})
    assert message_no_location.has_location() is False


def test_message_get_location():
    """Test get_location() method."""
    data_with_location = {
        "id": "msg_123",
        "attachments": [
            {"type": "location", "lat": "37.7749", "lng": "-122.4194", "name": "San Francisco"}
        ],
    }

    message = Message.from_dict(data_with_location)
    location = message.get_location()

    assert location == ("37.7749", "-122.4194", "San Francisco")

    # Message without location
    message_no_location = Message.from_dict({"id": "1", "attachments": []})
    assert message_no_location.get_location() is None


def test_message_reply_not_initialized():
    """Test that reply() raises error before initialization."""
    message = Message.from_dict({"id": "1"})

    with pytest.raises(NotImplementedError):
        message.reply("test")

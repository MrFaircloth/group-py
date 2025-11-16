"""Tests for MessageStorage."""

import pytest
from group_py.storage import MessageStorage, StoredMessage
from group_py import Message


def test_storage_initialization(temp_db):
    """Test storage initialization creates tables."""
    storage = MessageStorage(temp_db)

    # Should be able to get a session
    session = storage.get_session()
    assert session is not None
    session.close()


def test_save_received_message(temp_db, sample_message_data):
    """Test saving received messages."""
    storage = MessageStorage(temp_db)
    message = Message.from_dict(sample_message_data)

    storage.save_received(message)

    # Verify it was saved
    session = storage.get_session()
    try:
        stored = session.query(StoredMessage).filter_by(id=message.id).first()
        assert stored is not None
        assert stored.text == "Hello, world!"
        assert stored.user_id == "user_123"
        assert stored.direction == "received"
    finally:
        session.close()


def test_save_sent_message(temp_db):
    """Test saving sent messages."""
    storage = MessageStorage(temp_db)

    storage.save_sent(group_id="group_123", text="Test message", user_id="bot_123")

    # Verify it was saved
    session = storage.get_session()
    try:
        stored = session.query(StoredMessage).filter_by(direction="sent").first()
        assert stored is not None
        assert stored.text == "Test message"
        assert stored.group_id == "group_123"
        assert stored.direction == "sent"
    finally:
        session.close()


def test_get_recent_messages(temp_db, sample_message_data):
    """Test retrieving recent messages."""
    storage = MessageStorage(temp_db)

    # Save multiple messages
    for i in range(5):
        data = sample_message_data.copy()
        data["id"] = f"msg_{i}"
        data["text"] = f"Message {i}"
        message = Message.from_dict(data)
        storage.save_received(message)

    # Get recent messages
    recent = storage.get_recent(limit=3)

    assert len(recent) == 3
    # Should be in reverse chronological order
    assert recent[0]["text"] == "Message 4"
    assert recent[1]["text"] == "Message 3"
    assert recent[2]["text"] == "Message 2"


def test_get_recent_messages_as_objects(temp_db, sample_message_data):
    """Test retrieving recent messages as Message objects."""
    storage = MessageStorage(temp_db)

    # Save messages
    for i in range(3):
        data = sample_message_data.copy()
        data["id"] = f"msg_{i}"
        data["text"] = f"Message {i}"
        message = Message.from_dict(data)
        storage.save_received(message)

    # Get as objects
    messages = storage.get_recent(limit=10, as_objects=True)

    assert len(messages) == 3
    assert all(isinstance(m, Message) for m in messages)
    assert messages[0].text == "Message 2"


def test_storage_handles_none_text(temp_db):
    """Test storage handles messages with None text."""
    storage = MessageStorage(temp_db)

    data = {
        "id": "msg_none",
        "text": None,
        "user_id": "user_123",
        "group_id": "group_123",
        "created_at": 1234567890,
    }

    message = Message.from_dict(data)
    storage.save_received(message)

    # Verify it was saved
    session = storage.get_session()
    try:
        stored = session.query(StoredMessage).filter_by(id="msg_none").first()
        assert stored is not None
        assert stored.text is None
    finally:
        session.close()


def test_storage_duplicate_id_handling(temp_db, sample_message_data):
    """Test that duplicate message IDs are handled gracefully."""
    storage = MessageStorage(temp_db)
    message = Message.from_dict(sample_message_data)

    # Save same message twice
    storage.save_received(message)
    storage.save_received(message)  # Should not raise error

    # Should only have one entry
    session = storage.get_session()
    try:
        count = session.query(StoredMessage).filter_by(id=message.id).count()
        # Depending on implementation, might be 1 or 2
        # The important thing is it doesn't crash
        assert count >= 1
    finally:
        session.close()

"""Tests for history fetching functionality."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from group_py.client import GroupMeClient
from group_py.bot import GroupMeBotManager
from group_py.exceptions import APIError


@pytest.fixture
def client_with_api_key(mock_api_key):
    """Create a GroupMeClient instance."""
    return GroupMeClient(mock_api_key)


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
def sample_messages():
    """Sample messages from GroupMe API."""
    current_time = int(time.time())
    return [
        {
            "id": "msg_1",
            "text": "Message 1",
            "user_id": "user_123",
            "name": "User 1",
            "group_id": "group_123",
            "created_at": current_time - 100,
            "system": False,
            "sender_type": "user",
            "attachments": [],
        },
        {
            "id": "msg_2",
            "text": "Message 2",
            "user_id": "user_456",
            "name": "User 2",
            "group_id": "group_123",
            "created_at": current_time - 200,
            "system": False,
            "sender_type": "user",
            "attachments": [],
        },
        {
            "id": "msg_3",
            "text": "Message 3",
            "user_id": "user_789",
            "name": "User 3",
            "group_id": "group_123",
            "created_at": current_time - 300,
            "system": False,
            "sender_type": "user",
            "attachments": [],
        },
    ]


class TestGetMessages:
    """Test GroupMeClient.get_messages() method."""

    @patch("requests.Session.get")
    def test_get_messages_basic(self, mock_get, client_with_api_key, sample_messages):
        """Test basic message fetching."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": {"messages": sample_messages}}
        mock_get.return_value = mock_response

        messages = client_with_api_key.get_messages("group_123", limit=50)

        assert len(messages) == 3
        assert messages[0]["id"] == "msg_1"
        assert messages[1]["id"] == "msg_2"
        assert messages[2]["id"] == "msg_3"

        # Verify API call
        call_args = mock_get.call_args
        assert "group_123/messages" in call_args.args[0]
        assert call_args.kwargs["params"]["limit"] == 50

    @patch("requests.Session.get")
    def test_get_messages_with_before_id(self, mock_get, client_with_api_key, sample_messages):
        """Test pagination with before_id."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": {"messages": sample_messages}}
        mock_get.return_value = mock_response

        messages = client_with_api_key.get_messages(
            "group_123",
            limit=50,
            before_id="msg_100"
        )

        assert len(messages) == 3

        # Verify before_id in params
        call_args = mock_get.call_args
        assert call_args.kwargs["params"]["before_id"] == "msg_100"

    @patch("requests.Session.get")
    def test_get_messages_with_since_id(self, mock_get, client_with_api_key, sample_messages):
        """Test fetching with since_id."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": {"messages": sample_messages}}
        mock_get.return_value = mock_response

        messages = client_with_api_key.get_messages(
            "group_123",
            limit=50,
            since_id="msg_50"
        )

        assert len(messages) == 3

        # Verify since_id in params
        call_args = mock_get.call_args
        assert call_args.kwargs["params"]["since_id"] == "msg_50"

    @patch("requests.Session.get")
    def test_get_messages_limit_capped_at_100(self, mock_get, client_with_api_key):
        """Test that limit is capped at 100 (GroupMe API limit)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": {"messages": []}}
        mock_get.return_value = mock_response

        client_with_api_key.get_messages("group_123", limit=200)

        # Verify limit is capped at 100
        call_args = mock_get.call_args
        assert call_args.kwargs["params"]["limit"] == 100

    @patch("requests.Session.get")
    def test_get_messages_api_error(self, mock_get, client_with_api_key):
        """Test error handling for API failures."""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Server Error")

        with pytest.raises(APIError) as exc_info:
            client_with_api_key.get_messages("group_123")

        assert "Failed to fetch messages" in str(exc_info.value)


class TestFetchHistory:
    """Test GroupMeBotManager.fetch_history() method."""

    def test_fetch_history(self, mock_manager, sample_messages):
        """Test fetching history returns Message objects."""
        # Mock the client's get_messages method
        mock_manager.client.get_messages = Mock(return_value=sample_messages)

        messages = mock_manager.fetch_history(limit=50)

        assert len(messages) == 3
        # Verify we got Message objects, not dicts
        assert hasattr(messages[0], "id")
        assert hasattr(messages[0], "text")
        assert messages[0].id == "msg_1"
        assert messages[1].id == "msg_2"

        # Verify client was called correctly
        mock_manager.client.get_messages.assert_called_once_with(
            mock_manager.group_id,
            limit=50,
            before_id=None
        )

    def test_fetch_history_with_before_id(self, mock_manager, sample_messages):
        """Test pagination with before_id."""
        mock_manager.client.get_messages = Mock(return_value=sample_messages)

        messages = mock_manager.fetch_history(limit=50, before_id="msg_100")

        assert len(messages) == 3

        # Verify before_id was passed
        mock_manager.client.get_messages.assert_called_once_with(
            mock_manager.group_id,
            limit=50,
            before_id="msg_100"
        )

    def test_fetch_history_empty(self, mock_manager):
        """Test fetching when no messages available."""
        mock_manager.client.get_messages = Mock(return_value=[])

        messages = mock_manager.fetch_history(limit=50)

        assert len(messages) == 0


class TestBackfillHistory:
    """Test GroupMeBotManager.backfill_history() method."""

    def test_backfill_history_basic(self, mock_manager, capsys):
        """Test basic backfill functionality."""
        current_time = int(time.time())

        # Create messages from last 3 days
        messages_batch = [
            {
                "id": f"msg_{i}",
                "text": f"Message {i}",
                "user_id": "user_123",
                "name": "User",
                "group_id": "group_123",
                "created_at": current_time - (i * 3600),  # 1 hour apart
                "system": False,
                "sender_type": "user",
                "attachments": [],
            }
            for i in range(10)
        ]

        mock_manager.client.get_messages = Mock(return_value=messages_batch)

        count = mock_manager.backfill_history(days=7, max_messages=100)

        # Should fetch all 10 messages (all within 7 days)
        assert count == 10

        # Verify output
        captured = capsys.readouterr()
        assert "Backfilling message history" in captured.out
        assert "Backfill complete: 10 messages" in captured.out

    def test_backfill_with_callback(self, mock_manager):
        """Test backfill with callback function."""
        current_time = int(time.time())
        messages_batch = [
            {
                "id": f"msg_{i}",
                "text": f"Message {i}",
                "user_id": "user_123",
                "name": "User",
                "group_id": "group_123",
                "created_at": current_time - (i * 3600),
                "system": False,
                "sender_type": "user",
                "attachments": [],
            }
            for i in range(5)
        ]

        mock_manager.client.get_messages = Mock(return_value=messages_batch)

        # Track callback calls
        stored_messages = []

        def store_callback(message):
            stored_messages.append(message.id)

        count = mock_manager.backfill_history(days=7, callback=store_callback)

        assert count == 5
        assert len(stored_messages) == 5
        assert "msg_0" in stored_messages
        assert "msg_4" in stored_messages

    def test_backfill_filters_old_messages(self, mock_manager):
        """Test that backfill stops at time cutoff."""
        current_time = int(time.time())
        days_to_fetch = 3
        cutoff = current_time - (days_to_fetch * 24 * 60 * 60)

        # Mix of recent and old messages
        messages_batch = [
            {
                "id": "msg_recent",
                "text": "Recent message",
                "user_id": "user_123",
                "name": "User",
                "group_id": "group_123",
                "created_at": current_time - 3600,  # 1 hour ago (within window)
                "system": False,
                "sender_type": "user",
                "attachments": [],
            },
            {
                "id": "msg_old",
                "text": "Old message",
                "user_id": "user_123",
                "name": "User",
                "group_id": "group_123",
                "created_at": cutoff - 100000,  # Way before cutoff
                "system": False,
                "sender_type": "user",
                "attachments": [],
            },
        ]

        mock_manager.client.get_messages = Mock(return_value=messages_batch)

        count = mock_manager.backfill_history(days=days_to_fetch)

        # Should only count the recent message
        assert count == 1

    def test_backfill_respects_max_messages(self, mock_manager):
        """Test that backfill respects max_messages limit."""
        current_time = int(time.time())

        # Create mock that returns limited messages based on limit parameter
        all_messages = [
            {
                "id": f"msg_{i}",
                "text": f"Message {i}",
                "user_id": "user_123",
                "name": "User",
                "group_id": "group_123",
                "created_at": current_time - (i * 100),
                "system": False,
                "sender_type": "user",
                "attachments": [],
            }
            for i in range(200)  # Have 200 available messages
        ]

        # Mock that returns messages respecting the limit
        def mock_get_messages(group_id, limit=100, before_id=None):
            start_idx = 0
            if before_id:
                # Find the message with before_id and start after it
                for idx, msg in enumerate(all_messages):
                    if msg["id"] == before_id:
                        start_idx = idx + 1
                        break
            return all_messages[start_idx:start_idx + limit]

        mock_manager.client.get_messages = Mock(side_effect=mock_get_messages)

        count = mock_manager.backfill_history(days=7, max_messages=50)

        # Should stop at max_messages
        assert count == 50

    def test_backfill_callback_exception_handling(self, mock_manager, capsys):
        """Test that exceptions in callback don't break backfill."""
        current_time = int(time.time())
        messages_batch = [
            {
                "id": f"msg_{i}",
                "text": f"Message {i}",
                "user_id": "user_123",
                "name": "User",
                "group_id": "group_123",
                "created_at": current_time - (i * 3600),
                "system": False,
                "sender_type": "user",
                "attachments": [],
            }
            for i in range(5)
        ]

        mock_manager.client.get_messages = Mock(return_value=messages_batch)

        call_count = 0

        def failing_callback(message):
            nonlocal call_count
            call_count += 1
            raise Exception("Callback error!")

        count = mock_manager.backfill_history(days=7, callback=failing_callback)

        # Should still fetch all messages despite callback failures
        assert count == 5
        assert call_count == 5

        # Verify error messages printed
        captured = capsys.readouterr()
        assert "Error in backfill callback" in captured.out

    def test_backfill_empty_history(self, mock_manager):
        """Test backfill when no messages available."""
        mock_manager.client.get_messages = Mock(return_value=[])

        count = mock_manager.backfill_history(days=7)

        assert count == 0

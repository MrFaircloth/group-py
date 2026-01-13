"""Tests for message.post() method and deprecated reply()."""

import pytest
import warnings
from unittest.mock import Mock, patch
from group_py.models import Message


class TestPostMethod:
    """Tests for Message.post() method."""

    def test_post_without_callback_raises_error(self):
        """Test that post() without callback raises NotImplementedError."""
        message = Message.from_dict({
            'id': 'msg_1',
            'text': 'Hello',
            'user_id': 'user_1',
            'name': 'Test User',
            'group_id': 'group_1',
            'created_at': 1234567890,
            'system': False,
            'sender_type': 'user',
        })

        with pytest.raises(NotImplementedError) as exc_info:
            message.post("Response")

        assert "Post method not initialized" in str(exc_info.value)

    def test_post_with_callback(self):
        """Test that post() calls the injected callback."""
        message = Message.from_dict({
            'id': 'msg_1',
            'text': 'Hello',
            'user_id': 'user_1',
            'name': 'Test User',
            'group_id': 'group_1',
            'created_at': 1234567890,
            'system': False,
            'sender_type': 'user',
        })

        mock_callback = Mock(return_value={'response': 'ok'})
        message._send_callback = mock_callback

        result = message.post("Response text")

        mock_callback.assert_called_once_with("Response text")
        assert result == {'response': 'ok'}

    def test_post_with_kwargs(self):
        """Test that post() passes kwargs to callback."""
        message = Message.from_dict({
            'id': 'msg_1',
            'text': 'Hello',
            'user_id': 'user_1',
            'name': 'Test User',
            'group_id': 'group_1',
            'created_at': 1234567890,
            'system': False,
            'sender_type': 'user',
        })

        mock_callback = Mock(return_value={'response': 'ok'})
        message._send_callback = mock_callback

        message.post(
            "Hey @User!",
            image_url="https://example.com/image.jpg",
            mentions=[{"user_id": "123", "name": "User"}]
        )

        mock_callback.assert_called_once_with(
            "Hey @User!",
            image_url="https://example.com/image.jpg",
            mentions=[{"user_id": "123", "name": "User"}]
        )


class TestReplyDeprecation:
    """Tests for deprecated Message.reply() method."""

    def test_reply_shows_deprecation_warning(self):
        """Test that reply() shows DeprecationWarning."""
        message = Message.from_dict({
            'id': 'msg_1',
            'text': 'Hello',
            'user_id': 'user_1',
            'name': 'Test User',
            'group_id': 'group_1',
            'created_at': 1234567890,
            'system': False,
            'sender_type': 'user',
        })

        mock_callback = Mock(return_value={'response': 'ok'})
        message._send_callback = mock_callback

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            message.reply("Response")

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "post()" in str(w[0].message)
            assert "removed in v4.0" in str(w[0].message)

    def test_reply_calls_post(self):
        """Test that reply() delegates to post()."""
        message = Message.from_dict({
            'id': 'msg_1',
            'text': 'Hello',
            'user_id': 'user_1',
            'name': 'Test User',
            'group_id': 'group_1',
            'created_at': 1234567890,
            'system': False,
            'sender_type': 'user',
        })

        mock_callback = Mock(return_value={'response': 'ok'})
        message._send_callback = mock_callback

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = message.reply("Response", image_url="https://test.jpg")

        mock_callback.assert_called_once_with("Response", image_url="https://test.jpg")
        assert result == {'response': 'ok'}

    def test_reply_without_callback_raises_error(self):
        """Test that reply() raises error when callback not set."""
        message = Message.from_dict({
            'id': 'msg_1',
            'text': 'Hello',
            'user_id': 'user_1',
            'name': 'Test User',
            'group_id': 'group_1',
            'created_at': 1234567890,
            'system': False,
            'sender_type': 'user',
        })

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with pytest.raises(NotImplementedError):
                message.reply("Response")


class TestBotManagerIntegration:
    """Test post() integration with GroupMeBotManager."""

    @patch('group_py.bot.GroupMeClient')
    def test_manager_injects_callback(self, mock_client_class):
        """Test that manager injects _send_callback."""
        from group_py import GroupMeBotManager

        # Setup mock
        mock_client = Mock()
        mock_client.list_bots.return_value = []
        mock_client.find_bot.return_value = None
        mock_client.create_bot.return_value = {'response': {'bot': {'bot_id': 'test_bot_123'}}}
        mock_client_class.return_value = mock_client

        manager = GroupMeBotManager(api_key="test_key", group_id="test_group")

        # Track what post() was called with
        posted_messages = []

        @manager.command("test")
        def test_cmd(message, args):
            message.post(f"You said: {args}")
            posted_messages.append(True)

        # Process a webhook
        with patch.object(manager.primary_bot, 'send_message') as mock_send:
            manager.process_webhook({
                'id': 'msg_1',
                'text': 'test hello',
                'user_id': 'user_1',
                'name': 'Test User',
                'group_id': 'test_group',
                'created_at': 1234567890,
                'system': False,
                'sender_type': 'user',
            })

            assert len(posted_messages) == 1
            mock_send.assert_called_once_with("You said: hello")

    @patch('group_py.bot.GroupMeClient')
    def test_deprecated_reply_still_works(self, mock_client_class):
        """Test that deprecated reply() still works via manager."""
        from group_py import GroupMeBotManager

        # Setup mock
        mock_client = Mock()
        mock_client.list_bots.return_value = []
        mock_client.find_bot.return_value = None
        mock_client.create_bot.return_value = {'response': {'bot': {'bot_id': 'test_bot_123'}}}
        mock_client_class.return_value = mock_client

        manager = GroupMeBotManager(api_key="test_key", group_id="test_group")

        @manager.command("old")
        def old_cmd(message, args):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                message.reply(f"Old style: {args}")

        # Process a webhook
        with patch.object(manager.primary_bot, 'send_message') as mock_send:
            manager.process_webhook({
                'id': 'msg_1',
                'text': 'old test',
                'user_id': 'user_1',
                'name': 'Test User',
                'group_id': 'test_group',
                'created_at': 1234567890,
                'system': False,
                'sender_type': 'user',
            })

            mock_send.assert_called_once_with("Old style: test")

"""Tests for real-time WebSocket client."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, call
from group_py.realtime import FayeClient, RealtimeManager


class TestFayeClient:
    """Test FayeClient Bayeux protocol implementation."""

    @pytest.fixture
    def mock_callback(self):
        """Create a mock message callback."""
        return Mock()

    @pytest.fixture
    def faye_client(self, mock_callback):
        """Create a FayeClient instance with mock callback."""
        return FayeClient(
            user_id="test_user_123",
            group_id="test_group_456",
            on_message=mock_callback,
            reconnect=False  # Disable reconnect for tests
        )

    def test_initialization(self, faye_client, mock_callback):
        """Test FayeClient initializes with correct parameters."""
        assert faye_client.user_id == "test_user_123"
        assert faye_client.group_id == "test_group_456"
        assert faye_client.on_message == mock_callback
        assert faye_client.reconnect is False
        assert faye_client.connected is False
        assert faye_client.client_id is None
        assert faye_client._message_id == 0

    def test_next_message_id(self, faye_client):
        """Test message ID generation increments correctly."""
        assert faye_client._next_message_id() == 1
        assert faye_client._next_message_id() == 2
        assert faye_client._next_message_id() == 3

    def test_handshake_message_format(self, faye_client):
        """Test handshake message has correct Bayeux format."""
        faye_client.ws = Mock()
        faye_client.connected = True

        faye_client._handshake()

        # Verify send was called
        faye_client.ws.send.assert_called_once()

        # Parse the sent message
        sent_data = faye_client.ws.send.call_args[0][0]
        messages = json.loads(sent_data)
        handshake = messages[0]

        # Verify handshake structure
        assert handshake["channel"] == "/meta/handshake"
        assert handshake["version"] == "1.0"
        assert handshake["supportedConnectionTypes"] == ["websocket"]
        assert "id" in handshake

    def test_subscribe_message_format(self, faye_client):
        """Test subscribe message has correct Bayeux format."""
        faye_client.ws = Mock()
        faye_client.connected = True
        faye_client.client_id = "test_client_123"

        faye_client._subscribe()

        # Should send two subscribe messages
        assert faye_client.ws.send.call_count == 2

        # Check user subscription
        first_call = faye_client.ws.send.call_args_list[0][0][0]
        user_sub = json.loads(first_call)[0]
        assert user_sub["channel"] == "/meta/subscribe"
        assert user_sub["clientId"] == "test_client_123"
        assert user_sub["subscription"] == "/user/test_user_123"

        # Check group subscription
        second_call = faye_client.ws.send.call_args_list[1][0][0]
        group_sub = json.loads(second_call)[0]
        assert group_sub["channel"] == "/meta/subscribe"
        assert group_sub["subscription"] == "/group/test_group_456"

    def test_connect_message_format(self, faye_client):
        """Test connect message has correct Bayeux format."""
        faye_client.ws = Mock()
        faye_client.connected = True
        faye_client.client_id = "test_client_123"

        faye_client._connect()

        sent_data = faye_client.ws.send.call_args[0][0]
        messages = json.loads(sent_data)
        connect = messages[0]

        assert connect["channel"] == "/meta/connect"
        assert connect["clientId"] == "test_client_123"
        assert connect["connectionType"] == "websocket"

    def test_handle_handshake_success(self, faye_client):
        """Test successful handshake response."""
        faye_client.ws = Mock()
        faye_client.connected = True

        handshake_response = {
            "channel": "/meta/handshake",
            "successful": True,
            "clientId": "received_client_id_789"
        }

        with patch.object(faye_client, '_subscribe') as mock_subscribe, \
             patch.object(faye_client, '_connect') as mock_connect:

            faye_client._handle_message(handshake_response)

            # Should set client_id and call subscribe/connect
            assert faye_client.client_id == "received_client_id_789"
            mock_subscribe.assert_called_once()
            mock_connect.assert_called_once()

    def test_handle_handshake_failure(self, faye_client):
        """Test failed handshake response."""
        handshake_response = {
            "channel": "/meta/handshake",
            "successful": False,
            "error": "Authentication failed"
        }

        with patch.object(faye_client, '_subscribe') as mock_subscribe:
            faye_client._handle_message(handshake_response)

            # Should NOT set client_id or subscribe
            assert faye_client.client_id is None
            mock_subscribe.assert_not_called()

    def test_handle_subscribe_success(self, faye_client):
        """Test successful subscribe response."""
        subscribe_response = {
            "channel": "/meta/subscribe",
            "successful": True,
            "subscription": "/user/test_user_123"
        }

        # Should not raise any exceptions
        faye_client._handle_message(subscribe_response)

    def test_handle_connect_success(self, faye_client):
        """Test successful connect response triggers another connect."""
        faye_client.client_id = "test_client"
        faye_client.ws = Mock()
        faye_client.connected = True

        connect_response = {
            "channel": "/meta/connect",
            "successful": True
        }

        faye_client._handle_message(connect_response)

        # Should send another connect to maintain connection
        assert faye_client.connected is True
        # The _connect call will try to send
        assert faye_client.ws.send.called

    def test_event_filtering_typing(self, faye_client, mock_callback):
        """Test typing events are filtered out."""
        typing_event = {
            "channel": "/user/test_user_123",
            "data": {
                "type": "typing",
                "subject": {
                    "user_id": "someone",
                    "text": ""
                }
            }
        }

        faye_client._handle_message(typing_event)

        # Callback should NOT be called for typing events
        mock_callback.assert_not_called()

    def test_event_filtering_ping(self, faye_client, mock_callback):
        """Test ping events are filtered out."""
        ping_event = {
            "channel": "/user/test_user_123",
            "data": {
                "type": "ping",
                "subject": {}
            }
        }

        faye_client._handle_message(ping_event)

        # Callback should NOT be called for ping events
        mock_callback.assert_not_called()

    def test_message_routing_line_create(self, faye_client, mock_callback):
        """Test line.create events are routed to callback."""
        message_event = {
            "channel": "/user/test_user_123",
            "data": {
                "type": "line.create",
                "subject": {
                    "id": "msg_123",
                    "text": "Hello, world!",
                    "user_id": "sender_456",
                    "name": "Test User"
                }
            }
        }

        faye_client._handle_message(message_event)

        # Callback should be called with subject data
        mock_callback.assert_called_once()
        call_args = mock_callback.call_args[0][0]
        assert call_args["id"] == "msg_123"
        assert call_args["text"] == "Hello, world!"

    def test_message_routing_system_event(self, faye_client, mock_callback):
        """Test system events are routed to callback."""
        system_event = {
            "channel": "/user/test_user_123",
            "data": {
                "type": "system",
                "subject": {
                    "id": "sys_123",
                    "text": "User joined group",
                    "system": True
                }
            }
        }

        faye_client._handle_message(system_event)

        # Callback should be called
        mock_callback.assert_called_once()

    def test_callback_exception_handling(self, faye_client):
        """Test that exceptions in callback don't crash the client."""
        # Create callback that raises exception
        failing_callback = Mock(side_effect=Exception("Callback failed!"))
        faye_client.on_message = failing_callback

        message_event = {
            "channel": "/user/test_user_123",
            "data": {
                "type": "line.create",
                "subject": {"text": "Test"}
            }
        }

        # Should not raise exception
        faye_client._handle_message(message_event)

    def test_on_ws_message_array(self, faye_client):
        """Test WebSocket message handler with array of messages."""
        messages_array = [
            {"channel": "/meta/handshake", "successful": True, "clientId": "test"},
            {"channel": "/meta/subscribe", "successful": True}
        ]

        with patch.object(faye_client, '_handle_message') as mock_handle:
            faye_client._on_ws_message(None, json.dumps(messages_array))

            # Should call _handle_message for each message
            assert mock_handle.call_count == 2

    def test_on_ws_message_single(self, faye_client):
        """Test WebSocket message handler with single message (not array)."""
        single_message = {"channel": "/meta/handshake", "successful": True}

        with patch.object(faye_client, '_handle_message') as mock_handle:
            faye_client._on_ws_message(None, json.dumps(single_message))

            # Should call _handle_message once
            mock_handle.assert_called_once_with(single_message)

    def test_on_ws_open(self, faye_client):
        """Test WebSocket open callback."""
        with patch.object(faye_client, '_handshake') as mock_handshake:
            faye_client._on_ws_open(None)

            assert faye_client.connected is True
            mock_handshake.assert_called_once()

    def test_on_ws_close_no_reconnect(self, faye_client):
        """Test WebSocket close callback without reconnect."""
        faye_client.reconnect = False
        faye_client.connected = True
        faye_client.client_id = "test_client"

        with patch.object(faye_client, 'start') as mock_start:
            faye_client._on_ws_close(None, 1000, "Normal close")

            assert faye_client.connected is False
            assert faye_client.client_id is None
            # Should NOT reconnect
            mock_start.assert_not_called()

    def test_on_ws_close_with_reconnect(self):
        """Test WebSocket close callback with reconnect enabled."""
        callback = Mock()
        client = FayeClient(
            user_id="test",
            group_id="test",
            on_message=callback,
            reconnect=True,
            reconnect_delay=0  # No delay for test
        )
        client.connected = True

        with patch.object(client, 'start') as mock_start:
            client._on_ws_close(None, 1000, "Normal close")

            # Should attempt reconnect
            mock_start.assert_called_once()

    def test_on_ws_close_stop_requested(self):
        """Test WebSocket close does not reconnect when stop requested."""
        callback = Mock()
        client = FayeClient(
            user_id="test",
            group_id="test",
            on_message=callback,
            reconnect=True
        )
        client._stop_requested = True

        with patch.object(client, 'start') as mock_start:
            client._on_ws_close(None, 1000, "Normal close")

            # Should NOT reconnect when explicitly stopped
            mock_start.assert_not_called()

    @patch('group_py.realtime.WebSocketApp')
    @patch('group_py.realtime.threading.Thread')
    def test_start(self, mock_thread_class, mock_ws_class, faye_client):
        """Test starting the WebSocket client."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        mock_thread.is_alive.return_value = False

        faye_client.start()

        # Should create WebSocket with callbacks
        mock_ws_class.assert_called_once_with(
            "wss://push.groupme.com/faye",
            on_open=faye_client._on_ws_open,
            on_message=faye_client._on_ws_message,
            on_error=faye_client._on_ws_error,
            on_close=faye_client._on_ws_close,
        )

        # Should start thread
        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()

    @patch('group_py.realtime.WebSocketApp')
    @patch('group_py.realtime.threading.Thread')
    def test_start_already_running(self, mock_thread_class, mock_ws_class, faye_client):
        """Test starting when already running does nothing."""
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        faye_client._ws_thread = mock_thread

        faye_client.start()

        # Should not create new WebSocket
        mock_ws_class.assert_not_called()

    def test_stop(self, faye_client):
        """Test stopping the WebSocket client."""
        faye_client.ws = Mock()
        faye_client.reconnect = True

        faye_client.stop()

        # Should disable reconnect and close WebSocket
        assert faye_client.reconnect is False
        assert faye_client._stop_requested is True
        faye_client.ws.close.assert_called_once()


class TestRealtimeManager:
    """Test RealtimeManager wrapper class."""

    @pytest.fixture
    def mock_callback(self):
        """Create a mock callback."""
        return Mock()

    @pytest.fixture
    def realtime_manager(self, mock_callback):
        """Create a RealtimeManager instance."""
        return RealtimeManager(
            user_id="test_user",
            group_id="test_group",
            message_callback=mock_callback,
            reconnect=False
        )

    def test_initialization(self, realtime_manager, mock_callback):
        """Test RealtimeManager initializes FayeClient correctly."""
        assert realtime_manager.faye_client is not None
        assert realtime_manager.faye_client.user_id == "test_user"
        assert realtime_manager.faye_client.group_id == "test_group"
        assert realtime_manager.faye_client.on_message == mock_callback
        assert realtime_manager.faye_client.reconnect is False

    def test_start(self, realtime_manager):
        """Test RealtimeManager.start() calls FayeClient.start()."""
        with patch.object(realtime_manager.faye_client, 'start') as mock_start:
            realtime_manager.start()
            mock_start.assert_called_once()

    def test_stop(self, realtime_manager):
        """Test RealtimeManager.stop() calls FayeClient.stop()."""
        with patch.object(realtime_manager.faye_client, 'stop') as mock_stop:
            realtime_manager.stop()
            mock_stop.assert_called_once()

    def test_reconnect_enabled_by_default(self):
        """Test reconnect is enabled by default."""
        manager = RealtimeManager(
            user_id="test",
            group_id="test",
            message_callback=Mock()
        )
        assert manager.faye_client.reconnect is True

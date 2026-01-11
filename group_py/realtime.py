"""
Faye/Bayeux WebSocket client for GroupMe real-time events.

Implements the Bayeux protocol for real-time message reception from GroupMe's
push service. This is RECEIVE-ONLY - does not send typing indicators.
"""

import json
import threading
import time
import logging
from typing import Callable, Optional, Dict, Any
from websocket import WebSocketApp

logger = logging.getLogger(__name__)


class FayeClient:
    """
    GroupMe Faye/Bayeux protocol WebSocket client.

    Implements the Bayeux protocol for real-time message reception.
    This is RECEIVE-ONLY - does not send typing indicators.

    The Bayeux protocol flow:
    1. Connect to wss://push.groupme.com/faye
    2. Send handshake to get client_id
    3. Subscribe to /user/{user_id} channel
    4. Send connect messages to maintain connection
    5. Receive messages via WebSocket

    Example:
        def on_message(message_data):
            print(f"Received: {message_data}")

        client = FayeClient(
            user_id="your_user_id",
            group_id="your_group_id",
            on_message=on_message
        )
        client.start()

        # Stop when done
        client.stop()
    """

    PUSH_URL = "wss://push.groupme.com/faye"

    def __init__(
        self,
        user_id: str,
        group_id: str,
        on_message: Callable[[Dict[str, Any]], None],
        reconnect: bool = True,
        reconnect_delay: int = 5
    ):
        """
        Initialize Faye client.

        Args:
            user_id: GroupMe user ID (required for subscription)
            group_id: Group ID to monitor
            on_message: Callback function for received messages
            reconnect: Whether to auto-reconnect on disconnect (default: True)
            reconnect_delay: Seconds to wait before reconnecting (default: 5)
        """
        self.user_id = user_id
        self.group_id = group_id
        self.on_message = on_message
        self.reconnect = reconnect
        self.reconnect_delay = reconnect_delay

        self.ws: Optional[WebSocketApp] = None
        self.client_id: Optional[str] = None
        self.connected = False
        self._message_id = 0
        self._ws_thread: Optional[threading.Thread] = None
        self._stop_requested = False

    def _next_message_id(self) -> int:
        """Generate next message ID for Bayeux protocol."""
        self._message_id += 1
        return self._message_id

    def _send(self, message: Dict[str, Any]):
        """
        Send message over WebSocket.

        Args:
            message: Bayeux message dict
        """
        if self.ws and self.connected:
            payload = json.dumps([message])  # Bayeux uses arrays
            logger.debug(f"Sending: {payload}")
            self.ws.send(payload)

    def _handshake(self):
        """
        Perform Bayeux handshake to get client ID.

        This is the first step in the Bayeux protocol. The server responds
        with a client_id that we use for all subsequent messages.
        """
        handshake = {
            "channel": "/meta/handshake",
            "version": "1.0",
            "supportedConnectionTypes": ["websocket"],
            "id": self._next_message_id()
        }
        self._send(handshake)
        logger.info("Sent handshake")

    def _subscribe(self):
        """
        Subscribe to user and group channels.

        After handshake, we subscribe to:
        - /user/{user_id} - Receives messages sent to this user
        - /group/{group_id} - Receives typing indicators (we filter these out)
        """
        # Subscribe to user channel for messages
        user_subscribe = {
            "channel": "/meta/subscribe",
            "clientId": self.client_id,
            "subscription": f"/user/{self.user_id}",
            "id": self._next_message_id()
        }
        self._send(user_subscribe)

        # Subscribe to group channel for typing indicators (we'll filter them out)
        group_subscribe = {
            "channel": "/meta/subscribe",
            "clientId": self.client_id,
            "subscription": f"/group/{self.group_id}",
            "id": self._next_message_id()
        }
        self._send(group_subscribe)
        logger.info(f"Subscribed to /user/{self.user_id} and /group/{self.group_id}")

    def _connect(self):
        """
        Send connect message to maintain long-poll connection.

        The Bayeux protocol requires periodic connect messages to keep
        the connection alive. We send another connect after receiving
        a successful connect response.
        """
        connect = {
            "channel": "/meta/connect",
            "clientId": self.client_id,
            "connectionType": "websocket",
            "id": self._next_message_id()
        }
        self._send(connect)

    def _handle_message(self, message: Dict[str, Any]):
        """
        Route incoming Bayeux message.

        Args:
            message: Bayeux message dict with channel and data
        """
        channel = message.get("channel", "")

        if channel == "/meta/handshake":
            # Handshake response - get client_id
            if message.get("successful"):
                self.client_id = message.get("clientId")
                logger.info(f"Handshake successful, client_id: {self.client_id}")
                self._subscribe()
                self._connect()
            else:
                logger.error(f"Handshake failed: {message}")

        elif channel == "/meta/subscribe":
            # Subscribe response
            if message.get("successful"):
                logger.info(f"Subscribed to: {message.get('subscription')}")
            else:
                logger.error(f"Subscription failed: {message}")

        elif channel == "/meta/connect":
            # Connect response - send another connect to maintain connection
            if message.get("successful"):
                self.connected = True
                self._connect()  # Keep the connection alive
            else:
                logger.warning(f"Connect not successful: {message}")

        elif channel.startswith("/user/") or channel.startswith("/group/"):
            # Actual message data from subscribed channels
            data = message.get("data", {})
            event_type = data.get("type")

            # FILTER: Skip typing indicators and pings
            if event_type in ("typing", "ping"):
                logger.debug(f"Filtered {event_type} event")
                return

            # Process messages and system events
            if event_type in ("line.create", "system"):
                subject = data.get("subject", {})
                logger.info(f"Received message: {subject.get('text', '')[:50]}...")
                try:
                    self.on_message(subject)
                except Exception as e:
                    logger.error(f"Error in on_message callback: {e}", exc_info=True)

    def _on_ws_message(self, ws, raw_message):
        """
        WebSocket message callback.

        Args:
            ws: WebSocket instance
            raw_message: Raw message string from WebSocket
        """
        try:
            # Bayeux sends array of messages
            messages = json.loads(raw_message)
            if isinstance(messages, list):
                for msg in messages:
                    self._handle_message(msg)
            else:
                self._handle_message(messages)
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    def _on_ws_open(self, ws):
        """
        WebSocket open callback.

        Args:
            ws: WebSocket instance
        """
        logger.info("WebSocket connection opened")
        self.connected = True
        self._handshake()

    def _on_ws_close(self, ws, close_status_code, close_msg):
        """
        WebSocket close callback.

        Args:
            ws: WebSocket instance
            close_status_code: Status code
            close_msg: Close message
        """
        logger.info(f"WebSocket closed: {close_status_code} {close_msg}")
        self.connected = False
        self.client_id = None

        # Auto-reconnect if enabled and not explicitly stopped
        if self.reconnect and not self._stop_requested:
            logger.info(f"Reconnecting in {self.reconnect_delay} seconds...")
            time.sleep(self.reconnect_delay)
            self.start()

    def _on_ws_error(self, ws, error):
        """
        WebSocket error callback.

        Args:
            ws: WebSocket instance
            error: Error object
        """
        logger.error(f"WebSocket error: {error}")

    def start(self):
        """
        Start WebSocket connection in background thread.

        The WebSocket runs in a daemon thread and will automatically
        reconnect on disconnect if reconnect=True.

        Example:
            client = FayeClient(user_id="...", group_id="...", on_message=handler)
            client.start()
            # Client runs in background
        """
        if self._ws_thread and self._ws_thread.is_alive():
            logger.warning("WebSocket already running")
            return

        self._stop_requested = False

        self.ws = WebSocketApp(
            self.PUSH_URL,
            on_open=self._on_ws_open,
            on_message=self._on_ws_message,
            on_error=self._on_ws_error,
            on_close=self._on_ws_close,
        )

        self._ws_thread = threading.Thread(
            target=self.ws.run_forever,
            daemon=True  # Don't block program exit
        )
        self._ws_thread.start()
        logger.info("WebSocket client started")

    def stop(self):
        """
        Stop WebSocket connection.

        Prevents auto-reconnect and closes the WebSocket connection.

        Example:
            client.stop()
        """
        self._stop_requested = True
        self.reconnect = False
        if self.ws:
            self.ws.close()
        logger.info("WebSocket client stopped")


class RealtimeManager:
    """
    Manager for GroupMe real-time connections.

    Integrates with GroupMeBotManager to process real-time messages.
    This is a simple wrapper around FayeClient that provides a clean
    interface for starting/stopping real-time message reception.

    Example:
        def handle_message(message_data):
            bot_manager.process_webhook(message_data)

        manager = RealtimeManager(
            user_id="your_user_id",
            group_id="your_group_id",
            message_callback=handle_message
        )
        manager.start()

        # When done
        manager.stop()
    """

    def __init__(
        self,
        user_id: str,
        group_id: str,
        message_callback: Callable[[Dict[str, Any]], None],
        reconnect: bool = True
    ):
        """
        Initialize realtime manager.

        Args:
            user_id: GroupMe user ID
            group_id: Group ID to monitor
            message_callback: Callback to process received messages
            reconnect: Enable auto-reconnect (default: True)
        """
        self.faye_client = FayeClient(
            user_id=user_id,
            group_id=group_id,
            on_message=message_callback,
            reconnect=reconnect
        )

    def start(self):
        """
        Start receiving real-time messages.

        Connects to GroupMe's push service and begins receiving messages
        in the background.
        """
        self.faye_client.start()

    def stop(self):
        """
        Stop receiving real-time messages.

        Disconnects from push service and stops auto-reconnect.
        """
        self.faye_client.stop()

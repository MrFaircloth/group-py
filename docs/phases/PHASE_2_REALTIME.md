# Phase 2: Realtime WebSocket

**Duration:** 1-2 weeks (7-12 working days)

**Status:** 🔴 Not Started

**Branch:** `v3-realtime`

## Overview

Phase 2 adds real-time message reception via WebSocket as an alternative to webhooks. This enables bots to run without exposing an HTTP endpoint.

### What We're Building

1. **FayeClient** - Low-level Bayeux protocol WebSocket client
2. **RealtimeManager** - High-level integration with bot manager
3. **Auto-reconnect** - Handle disconnections gracefully
4. **Event filtering** - Skip ping/typing events
5. **Dual-mode support** - Webhook AND/OR WebSocket

### Key Features

- Connect to `wss://push.groupme.com/faye`
- Bayeux protocol implementation (handshake, subscribe, connect)
- Background thread execution
- Auto-reconnect on disconnect
- Filter out ping and typing events
- Route messages to same handlers as webhooks

---

## Prerequisites

- [x] **Phase 1 complete** and verified
- [ ] `websocket-client` library installed
- [ ] Understanding of Bayeux protocol
- [ ] Test group and user credentials

**Verify prerequisites:**
```bash
# Phase 1 complete
git log --oneline | head -1  # Should mention Phase 1

# Install websocket-client
pip install websocket-client>=1.8.0
```

---

## Task Breakdown

### Task 2.1: Create FayeClient (5-7 days)

**Files to create:**
- `group_py/realtime.py`

**Implementation Steps:**

#### Step 2.1.1: Create basic FayeClient class structure

**Create:** `group_py/realtime.py`

**Basic structure:**
```python
"""
Faye/Bayeux WebSocket client for GroupMe real-time events.
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

    Example:
        def on_message(message_data):
            print(f"Received: {message_data}")

        client = FayeClient(
            user_id="your_user_id",
            group_id="your_group_id",
            on_message=on_message
        )
        client.start()
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
        """Initialize Faye client."""
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

    def _next_message_id(self) -> int:
        """Generate next message ID for Bayeux protocol."""
        self._message_id += 1
        return self._message_id

    def start(self):
        """Start WebSocket connection in background thread."""
        # Implementation in next steps
        pass

    def stop(self):
        """Stop WebSocket connection."""
        # Implementation in next steps
        pass
```

#### Step 2.1.2: Implement Bayeux protocol methods

**Add to FayeClient:**

**Handshake:**
```python
def _handshake(self):
    """Perform Bayeux handshake to get client ID."""
    handshake = {
        "channel": "/meta/handshake",
        "version": "1.0",
        "supportedConnectionTypes": ["websocket"],
        "id": self._next_message_id()
    }
    self._send(handshake)
    logger.info("Sent handshake")
```

**Subscribe:**
```python
def _subscribe(self):
    """Subscribe to user and group channels."""
    # Subscribe to user channel for messages
    user_subscribe = {
        "channel": "/meta/subscribe",
        "clientId": self.client_id,
        "subscription": f"/user/{self.user_id}",
        "id": self._next_message_id()
    }
    self._send(user_subscribe)

    # Subscribe to group channel for typing (we'll filter it out)
    group_subscribe = {
        "channel": "/meta/subscribe",
        "clientId": self.client_id,
        "subscription": f"/group/{self.group_id}",
        "id": self._next_message_id()
    }
    self._send(group_subscribe)
    logger.info(f"Subscribed to /user/{self.user_id} and /group/{self.group_id}")
```

**Connect (maintain connection):**
```python
def _connect(self):
    """Send connect message to maintain long-poll connection."""
    connect = {
        "channel": "/meta/connect",
        "clientId": self.client_id,
        "connectionType": "websocket",
        "id": self._next_message_id()
    }
    self._send(connect)
```

**Send helper:**
```python
def _send(self, message: Dict[str, Any]):
    """Send message over WebSocket."""
    if self.ws and self.connected:
        payload = json.dumps([message])  # Bayeux uses arrays
        logger.debug(f"Sending: {payload}")
        self.ws.send(payload)
```

#### Step 2.1.3: Implement message routing

**Add message handler:**
```python
def _handle_message(self, message: Dict[str, Any]):
    """Route incoming Bayeux message."""
    channel = message.get("channel", "")

    if channel == "/meta/handshake":
        # Handshake response
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

    elif channel.startswith("/user/") or channel.startswith("/group/"):
        # Actual message data
        data = message.get("data", {})
        event_type = data.get("type")

        # FILTER: Skip typing indicators and pings
        if event_type in ("typing", "ping"):
            logger.debug(f"Filtered {event_type} event")
            return

        # Process messages and system events
        if event_type in ("line.create", "system"):
            subject = data.get("subject", {})
            logger.info(f"Received message: {subject.get('text', '')[:50]}")
            try:
                self.on_message(subject)
            except Exception as e:
                logger.error(f"Error in on_message callback: {e}")
```

#### Step 2.1.4: Implement WebSocket callbacks

**Add WebSocket event handlers:**
```python
def _on_ws_message(self, ws, raw_message):
    """WebSocket message callback."""
    try:
        # Bayeux sends array of messages
        messages = json.loads(raw_message)
        if isinstance(messages, list):
            for msg in messages:
                self._handle_message(msg)
        else:
            self._handle_message(messages)
    except Exception as e:
        logger.error(f"Error processing message: {e}")

def _on_ws_open(self, ws):
    """WebSocket open callback."""
    logger.info("WebSocket connection opened")
    self.connected = True
    self._handshake()

def _on_ws_close(self, ws, close_status_code, close_msg):
    """WebSocket close callback."""
    logger.info(f"WebSocket closed: {close_status_code} {close_msg}")
    self.connected = False

    if self.reconnect:
        logger.info(f"Reconnecting in {self.reconnect_delay} seconds...")
        time.sleep(self.reconnect_delay)
        self.start()

def _on_ws_error(self, ws, error):
    """WebSocket error callback."""
    logger.error(f"WebSocket error: {error}")
```

#### Step 2.1.5: Implement start/stop methods

**Complete start/stop:**
```python
def start(self):
    """Start WebSocket connection in background thread."""
    if self._ws_thread and self._ws_thread.is_alive():
        logger.warning("WebSocket already running")
        return

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
    """Stop WebSocket connection."""
    self.reconnect = False
    if self.ws:
        self.ws.close()
    logger.info("WebSocket client stopped")
```

#### Step 2.1.6: Write FayeClient tests

**Create:** `tests/unit/test_realtime.py`

**Tests to write:**
- `test_handshake_message_format()`
- `test_subscribe_message_format()`
- `test_event_filtering()` - Verify ping/typing filtered
- `test_message_routing()`
- `test_reconnect_on_disconnect()`

**Run tests:**
```bash
pytest tests/unit/test_realtime.py -v
```

**Acceptance Criteria:**
- ✅ FayeClient sends correct handshake
- ✅ Subscribes to correct channels
- ✅ Filters out ping/typing events
- ✅ Routes messages to callback
- ✅ Reconnects on disconnect
- ✅ All tests pass

---

### Task 2.2: Create RealtimeManager (2-3 days)

**Files to modify:**
- `group_py/realtime.py` (add RealtimeManager class)

**Implementation Steps:**

#### Step 2.2.1: Add RealtimeManager class

**Add to realtime.py:**
```python
class RealtimeManager:
    """
    Manager for GroupMe real-time connections.

    Integrates with GroupMeBotManager to process real-time messages.
    This is a simple wrapper around FayeClient.

    Example:
        def handle_message(message_data):
            bot_manager.process_webhook(message_data)

        manager = RealtimeManager(
            user_id="your_user_id",
            group_id="your_group_id",
            message_callback=handle_message
        )
        manager.start()
    """

    def __init__(
        self,
        user_id: str,
        group_id: str,
        message_callback: Callable[[Dict[str, Any]], None]
    ):
        """
        Initialize realtime manager.

        Args:
            user_id: GroupMe user ID
            group_id: Group ID to monitor
            message_callback: Callback to process received messages
        """
        self.faye_client = FayeClient(
            user_id=user_id,
            group_id=group_id,
            on_message=message_callback
        )

    def start(self):
        """Start receiving real-time messages."""
        self.faye_client.start()

    def stop(self):
        """Stop receiving real-time messages."""
        self.faye_client.stop()
```

**Acceptance Criteria:**
- ✅ RealtimeManager created
- ✅ Wraps FayeClient cleanly
- ✅ Simple start/stop interface

---

### Task 2.3: Integrate with Bot Manager (2-3 days)

**Files to modify:**
- `group_py/bot.py`
- `pyproject.toml`

**Implementation Steps:**

#### Step 2.3.1: Add realtime parameters to GroupMeBotManager

**Location:** `group_py/bot.py` in `__init__()`

**Add parameters:**
```python
def __init__(
    self,
    api_key: str = None,
    group_id: str = None,
    callback_url: Optional[str] = None,  # Now optional!
    bot_name: str = "System",
    bot_id: str = None,
    avatar_url: str = None,
    enable_realtime: bool = False,  # NEW
    user_id: str = None,            # NEW
):
```

**Add validation:**
```python
# Make callback_url optional if realtime is enabled
if not callback_url and not enable_realtime:
    logger.warning(
        "No callback_url or realtime mode - bot will not receive messages"
    )
```

#### Step 2.3.2: Initialize realtime manager

**Add to __init__():**
```python
# Realtime setup
self.realtime_manager: Optional[RealtimeManager] = None

if enable_realtime:
    # Get user_id from parameter or environment
    if not user_id:
        user_id = os.getenv("GROUPME_USER_ID")

    if not user_id:
        raise ConfigurationError(
            "user_id required for realtime mode. Set GROUPME_USER_ID "
            "environment variable or pass user_id to __init__"
        )

    from .realtime import RealtimeManager

    self.realtime_manager = RealtimeManager(
        user_id=user_id,
        group_id=self.group_id,
        message_callback=self._handle_realtime_message
    )
    self.realtime_manager.start()
    print(f"✓ Real-time WebSocket client started for user {user_id}")
```

#### Step 2.3.3: Add realtime message handler

**Add method to GroupMeBotManager:**
```python
def _handle_realtime_message(self, data: dict):
    """
    Process message received via WebSocket.

    Routes to same message handling pipeline as webhooks.
    This means all commands, handlers, etc. work identically
    whether the message came from webhook or WebSocket.

    Args:
        data: Message data dict from Faye client
    """
    # Just route through existing process_webhook logic!
    self.process_webhook(data)
```

#### Step 2.3.4: Add cleanup for realtime

**Update _cleanup() method:**
```python
def _cleanup(self):
    """Clean up on program exit."""
    # Stop realtime client
    if self.realtime_manager:
        self.realtime_manager.stop()

    # Destroy auto-created bots
    if self._auto_created and self.bot_id:
        try:
            self.client.destroy_bot(self.bot_id)
            print(f"✓ Destroyed bot {self.bot_id}")
        except Exception as e:
            print(f"⚠ Warning: Failed to destroy bot: {e}")
```

#### Step 2.3.5: Update from_yaml() to support realtime

**Modify from_yaml() method:**
```python
@classmethod
def from_yaml(cls, config_path: str) -> 'GroupMeBotManager':
    """Create bot manager from YAML configuration file."""
    from .config import load_yaml_config, get_config_value

    config = load_yaml_config(config_path)

    # Get realtime config
    realtime_config = config.get("realtime", {})
    enable_realtime = realtime_config.get("enabled", False)

    return cls(
        api_key=get_config_value(config, "api_key"),
        group_id=get_config_value(config, "group_id"),
        callback_url=get_config_value(config, "callback_url"),
        bot_name=get_config_value(config, "bot_name", "System"),
        bot_id=get_config_value(config, "bot_id"),
        avatar_url=get_config_value(config, "avatar_url"),
        user_id=get_config_value(config, "user_id"),
        enable_realtime=enable_realtime,  # NEW
    )
```

#### Step 2.3.6: Add websocket-client dependency

**Modify:** `pyproject.toml`

**Add dependency:**
```toml
dependencies = [
    "requests>=2.31.0",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0.0",
    "websocket-client>=1.8.0",  # NEW
]
```

#### Step 2.3.7: Write integration tests

**Create:** `tests/integration/test_realtime_live.py`

**Tests to write:**
- `test_realtime_connection()` - Connects successfully
- `test_receive_message_via_realtime()` - Receives messages
- `test_handlers_work_with_realtime()` - Commands work
- `test_reconnect()` - Reconnects after disconnect

**Run tests:**
```bash
pytest -m "integration and realtime" -v
```

**Acceptance Criteria:**
- ✅ `enable_realtime=True` works
- ✅ WebSocket connects on init
- ✅ Messages route to handlers
- ✅ Commands work identically to webhook mode
- ✅ Cleanup stops WebSocket
- ✅ Integration tests pass

---

## Verification Checklist

Before moving to Phase 3, verify:

### Code Quality
- [ ] All new code has type hints
- [ ] All new code has docstrings
- [ ] Logging added for debugging
- [ ] Error handling for WebSocket failures

### Testing
- [ ] Unit tests pass: `pytest tests/unit/test_realtime.py`
- [ ] Integration tests pass: `pytest -m "integration and realtime"`
- [ ] WebSocket connects successfully
- [ ] Messages route correctly

### Features
- [ ] FayeClient implements Bayeux protocol
- [ ] Handshake, subscribe, connect work
- [ ] Event filtering (ping/typing) works
- [ ] Auto-reconnect works
- [ ] Integration with bot manager works
- [ ] Both webhook AND realtime can run simultaneously

### Documentation
- [ ] Docstrings added with examples
- [ ] Logging helps debug connection issues

### Git
- [ ] All changes committed
- [ ] Meaningful commit messages

**Final verification:**
```bash
# Test WebSocket connection
python -c "
from group_py import GroupMeBotManager
manager = GroupMeBotManager(
    api_key='test',
    group_id='test',
    user_id='test',
    enable_realtime=True
)
import time; time.sleep(5)
print('✓ WebSocket started')
"
```

---

## Troubleshooting

### WebSocket connection fails

**Check:**
- Valid user_id provided
- Internet connection working
- GroupMe push service is up

### Messages not routing to handlers

**Check:**
- `_handle_realtime_message()` calls `process_webhook()`
- Handlers registered before messages arrive
- No exceptions in message processing

### Auto-reconnect not working

**Check:**
- `reconnect=True` in FayeClient
- `_on_ws_close()` calls `start()`
- Not hitting rate limits

---

## Next Steps

Once Phase 2 is complete:

1. **Commit Phase 2:**
   ```bash
   git add .
   git commit -m "Phase 2: Realtime WebSocket complete

   - Implement Faye/Bayeux WebSocket client
   - Add RealtimeManager for bot integration
   - Add enable_realtime parameter to bot manager
   - Add auto-reconnect on disconnect
   - Filter out ping/typing events
   - Add integration tests"
   ```

2. **Proceed to Phase 3:** [PHASE_3_DJANGO.md](./PHASE_3_DJANGO.md)

---

## Estimated Timeline

| Task | Duration | Dependencies |
|------|----------|--------------|
| 2.1 FayeClient | 5-7 days | Phase 1 |
| 2.2 RealtimeManager | 2-3 days | Task 2.1 |
| 2.3 Bot Integration | 2-3 days | Task 2.2 |

**Total: 9-13 days (1.5-2 weeks)**

# Phase 1: Foundation

**Duration:** 1 week (5 working days)

**Status:** 🔴 Not Started

**Branch:** `v3-realtime`

## Overview

Phase 1 establishes the foundation for v3.0.0 by adding core features and removing built-in storage. This phase makes the library lighter and more flexible.

### What We're Building

1. **Mentions Support** - Auto-calculate loci for @mentions
2. **YAML Configuration** - Load bot config from files
3. **Global Message Handler** - `@on_any_message` hook
4. **History Fetching** - Pull message history from API
5. **Remove Storage** - Delete built-in storage, make it user's responsibility

### Why This Phase Comes First

- Removes major dependency (SQLAlchemy)
- Establishes patterns for Phases 2-4
- Can be tested independently
- Non-breaking additions (except storage removal)

---

## Prerequisites

- [x] Git branch `v3-realtime` created
- [ ] All existing v2.0 tests pass
- [ ] Development environment set up

**Verify prerequisites:**
```bash
git branch --show-current  # Should show: v3-realtime
pytest -m "not integration"  # Should pass all unit tests
```

---

## Task Breakdown

### Task 1.1: Mentions Support (2 days)

**Files to modify:**
- `group_py/client.py`
- `group_py/sender.py`

**Implementation Steps:**

#### Step 1.1.1: Add `_build_mentions_attachment()` to `GroupMeClient`

**Location:** `group_py/client.py`

**Add method:**
```python
def _build_mentions_attachment(
    self,
    text: str,
    mentions: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Build mentions attachment with auto-calculated loci.

    Args:
        text: Message text
        mentions: List of {"user_id": "123", "name": "Bob"}

    Returns:
        Mentions attachment dict with format:
        {"type": "mentions", "user_ids": [...], "loci": [[start, length], ...]}

    Example:
        text = "Hey @Bob!"
        mentions = [{"user_id": "123", "name": "Bob"}]
        # Returns: {"type": "mentions", "user_ids": ["123"], "loci": [[4, 4]]}
    """
    user_ids = []
    loci = []

    for mention in mentions:
        name = mention["name"]
        user_id = mention["user_id"]

        # Find @name in text
        search_pattern = f"@{name}"
        index = text.find(search_pattern)

        if index != -1:
            user_ids.append(user_id)
            loci.append([index, len(search_pattern)])

    return {
        "type": "mentions",
        "user_ids": user_ids,
        "loci": loci
    }
```

#### Step 1.1.2: Update `send_message()` to accept mentions

**Location:** `group_py/client.py`

**Modify signature:**
```python
def send_message(
    self,
    text: str,
    image_url: Optional[str] = None,
    attachments: Optional[List[Dict]] = None,
    mentions: Optional[List[Dict[str, str]]] = None,  # NEW
) -> Dict[str, Any]:
```

**Add mentions logic:**
```python
# Inside send_message()
# Build attachments list
final_attachments = attachments.copy() if attachments else []

# Add mentions attachment if provided
if mentions:
    mentions_attachment = self._build_mentions_attachment(text, mentions)
    final_attachments.append(mentions_attachment)

if final_attachments:
    payload["attachments"] = final_attachments
```

#### Step 1.1.3: Update `GroupMeBot.send_message()` in sender.py

**Location:** `group_py/sender.py`

**Add mentions parameter** to match `GroupMeClient.send_message()` signature.

#### Step 1.1.4: Write tests

**Create:** `tests/unit/test_mentions.py`

**Tests to write:**
- `test_single_mention()` - Single @mention
- `test_multiple_mentions()` - Multiple @mentions
- `test_mention_not_found()` - @name not in text (should skip)
- `test_send_message_with_mentions()` - Integration with send_message

**Run tests:**
```bash
pytest tests/unit/test_mentions.py -v
```

**Acceptance Criteria:**
- ✅ `_build_mentions_attachment()` calculates loci correctly
- ✅ Single mentions work
- ✅ Multiple mentions work
- ✅ Mentions not in text are skipped
- ✅ `send_message(mentions=[...])` works
- ✅ All tests pass

---

### Task 1.2: YAML Configuration (2 days)

**Files to create:**
- `group_py/config.py`

**Files to modify:**
- `group_py/bot.py`

**Implementation Steps:**

#### Step 1.2.1: Create `config.py`

**Create:** `group_py/config.py`

**Implement:**
```python
"""YAML configuration loader for group-py."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml


class ConfigError(Exception):
    """Raised when configuration is invalid."""
    pass


def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """
    Load and validate YAML configuration file.

    Args:
        config_path: Path to YAML config file

    Returns:
        Validated configuration dict

    Raises:
        ConfigError: If config is invalid or file not found

    Example YAML:
        api_key: "your_api_key"
        group_id: "your_group_id"
        user_id: "your_user_id"

        realtime:
          enabled: true
          reconnect: true

        bots:
          - name: "System"
            primary: true
          - name: "Bean"
            bot_id: "existing_bot_id"
    """
    path = Path(config_path)

    if not path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        with open(path) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML: {e}")

    # Validate required fields
    if not config.get("api_key"):
        raise ConfigError("api_key is required in config")

    if not config.get("group_id"):
        raise ConfigError("group_id is required in config")

    return config


def get_config_value(config: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Get config value with environment variable fallback.

    Priority: Config file > Environment variable > Default

    Args:
        config: Config dict from YAML
        key: Config key to look up
        default: Default value if not found

    Returns:
        Config value
    """
    # Check config dict first
    if key in config:
        return config[key]

    # Check environment variable
    env_key = f"GROUPME_{key.upper()}"
    env_value = os.getenv(env_key)
    if env_value is not None:
        return env_value

    return default
```

#### Step 1.2.2: Add `from_yaml()` class method to `GroupMeBotManager`

**Location:** `group_py/bot.py`

**Add method:**
```python
@classmethod
def from_yaml(cls, config_path: str) -> 'GroupMeBotManager':
    """
    Create bot manager from YAML configuration file.

    Args:
        config_path: Path to YAML config file

    Returns:
        Initialized GroupMeBotManager

    Example:
        manager = GroupMeBotManager.from_yaml("bots.yaml")

    Config format:
        api_key: "your_api_key"
        group_id: "your_group_id"
        user_id: "your_user_id"  # optional

        realtime:
          enabled: false
          reconnect: true

        bots:
          - name: "System"
            primary: true
          - name: "Bean"
            bot_id: "existing_bot_id"
    """
    from .config import load_yaml_config, get_config_value

    config = load_yaml_config(config_path)

    # Extract manager config
    return cls(
        api_key=get_config_value(config, "api_key"),
        group_id=get_config_value(config, "group_id"),
        callback_url=get_config_value(config, "callback_url"),
        bot_name=get_config_value(config, "bot_name", "System"),
        bot_id=get_config_value(config, "bot_id"),
        avatar_url=get_config_value(config, "avatar_url"),
        user_id=get_config_value(config, "user_id"),
        # Note: enable_realtime will be added in Phase 2
    )
```

#### Step 1.2.3: Add pyyaml dependency

**Modify:** `pyproject.toml`

**Add to dependencies:**
```toml
dependencies = [
    "requests>=2.31.0",
    "python-dotenv>=1.0.0",
    "sqlalchemy>=2.0.0",  # Will be removed in Task 1.5
    "pyyaml>=6.0.0",  # NEW
]
```

#### Step 1.2.4: Write tests

**Create:** `tests/unit/test_config.py`

**Tests to write:**
- `test_load_valid_yaml()` - Load valid config
- `test_missing_api_key()` - Error if api_key missing
- `test_invalid_yaml()` - Error on malformed YAML
- `test_from_yaml()` - Create manager from YAML
- `test_env_var_fallback()` - Environment variable override

**Create:** `tests/test_config.yaml` (test fixture)

**Run tests:**
```bash
pytest tests/unit/test_config.py -v
```

**Acceptance Criteria:**
- ✅ YAML files load correctly
- ✅ Required fields validated
- ✅ `from_yaml()` creates manager
- ✅ Environment variable fallback works
- ✅ Clear error messages for invalid config
- ✅ All tests pass

---

### Task 1.3: Global Message Handler (1 day)

**Files to modify:**
- `group_py/bot.py`

**Implementation Steps:**

#### Step 1.3.1: Add `_preprocessors` list to `GroupMeBotManager`

**Location:** `group_py/bot.py` in `__init__()`

**Add:**
```python
# Handler storage
self._handlers: List[Callable] = []
self._commands: Dict[str, Callable] = {}
self._async_commands: Dict[str, tuple] = {}
self._unknown_command_handler: Optional[Callable] = None
self._preprocessors: List[Callable] = []  # NEW
```

#### Step 1.3.2: Add `on_any_message()` decorator

**Location:** `group_py/bot.py`

**Add method:**
```python
def on_any_message(self, func: Callable) -> Callable:
    """
    Decorator to register a global message handler.

    This handler runs for ALL messages BEFORE command routing.
    Perfect for: storage, logging, sanitization, analytics.

    Args:
        func: Handler function that takes (message)

    Returns:
        The original function (for decorator chaining)

    Example:
        @manager.on_any_message
        def store_all(message):
            # Runs for EVERY message (including commands)
            MyDatabase.save(message)
            print(f"[{message.name}]: {message.text}")

        @manager.on_any_message
        def sanitize(message):
            # Multiple handlers can be registered
            if message.text and has_profanity(message.text):
                message.text = censor(message.text)
    """
    self._preprocessors.append(func)
    return func
```

#### Step 1.3.3: Update `process_webhook()` to run preprocessors

**Location:** `group_py/bot.py` in `process_webhook()`

**Modify to run preprocessors FIRST:**
```python
def process_webhook(self, data: dict) -> None:
    """Process a GroupMe webhook payload."""
    # Parse the message
    message = Message.from_dict(data)

    # Inject reply functionality
    message.reply = lambda text, **kwargs: self.send_message(text, **kwargs)

    # Skip bot's own messages
    if message.sender_type == "bot":
        return

    # NEW: Run preprocessors FIRST (before any routing)
    for preprocessor in self._preprocessors:
        try:
            preprocessor(message)
        except Exception as e:
            print(f"⚠ Error in preprocessor {preprocessor.__name__}: {e}")

    # Continue with existing routing logic...
    # (commands, async_commands, handlers, etc.)
```

#### Step 1.3.4: Write tests

**Create:** `tests/unit/test_global_handlers.py`

**Tests to write:**
- `test_on_any_message_fires_for_all()` - Fires for all messages
- `test_on_any_message_fires_before_commands()` - Order of execution
- `test_multiple_preprocessors()` - Multiple handlers
- `test_preprocessor_exception_doesnt_break_routing()` - Error handling

**Run tests:**
```bash
pytest tests/unit/test_global_handlers.py -v
```

**Acceptance Criteria:**
- ✅ `@on_any_message` decorator works
- ✅ Preprocessors run before command routing
- ✅ Multiple preprocessors execute in order
- ✅ Exceptions don't break message routing
- ✅ All tests pass

---

### Task 1.4: History Fetching (1 day)

**Files to modify:**
- `group_py/client.py`
- `group_py/bot.py`

**Implementation Steps:**

#### Step 1.4.1: Add `get_messages()` to `GroupMeClient`

**Location:** `group_py/client.py`

**Add method:**
```python
def get_messages(
    self,
    group_id: str,
    limit: int = 100,
    before_id: Optional[str] = None,
    since_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch message history from GroupMe API.

    Args:
        group_id: Group ID to fetch messages from
        limit: Number of messages (max 100 per request)
        before_id: Get messages before this message ID (for pagination)
        since_id: Get messages after this message ID (for backfill)

    Returns:
        List of message dicts (newest first)

    Raises:
        APIError: If request fails

    Example:
        # Get recent messages
        messages = client.get_messages("group_123", limit=50)

        # Paginate
        oldest_id = messages[-1]["id"]
        older = client.get_messages("group_123", limit=50, before_id=oldest_id)
    """
    url = f"{self.BASE_URL}/groups/{group_id}/messages"
    params = {
        "token": self.api_key,
        "limit": min(limit, 100)  # Max 100 per request
    }

    if before_id:
        params["before_id"] = before_id
    if since_id:
        params["since_id"] = since_id

    try:
        response = self.session.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()["response"]["messages"]
    except requests.exceptions.RequestException as e:
        raise APIError(f"Failed to fetch messages: {e}")
```

#### Step 1.4.2: Add `fetch_history()` to `GroupMeBotManager`

**Location:** `group_py/bot.py`

**Add method:**
```python
def fetch_history(
    self,
    limit: int = 100,
    before_id: Optional[str] = None,
) -> List[Message]:
    """
    Fetch message history from GroupMe API.

    Args:
        limit: Number of messages to fetch (max 100)
        before_id: Get messages before this ID (for pagination)

    Returns:
        List of Message objects (newest first)

    Example:
        # Get recent messages
        messages = manager.fetch_history(limit=50)

        # Paginate through older messages
        oldest_id = messages[-1].id
        older = manager.fetch_history(limit=50, before_id=oldest_id)
    """
    raw_messages = self.client.get_messages(
        self.group_id,
        limit=limit,
        before_id=before_id
    )

    return [Message.from_dict(msg) for msg in raw_messages]
```

#### Step 1.4.3: Add `backfill_history()` convenience method

**Location:** `group_py/bot.py`

**Add method:**
```python
def backfill_history(
    self,
    days: int = 7,
    callback: Optional[Callable[[Message], None]] = None,
    max_messages: int = 1000
) -> int:
    """
    Backfill message history for the last N days.

    Useful for catching up on missed messages after bot restarts.

    Args:
        days: Number of days of history to fetch
        callback: Optional function to call for each message (for storage)
        max_messages: Maximum total messages to fetch

    Returns:
        Number of messages fetched

    Example:
        # Backfill last 3 days on startup
        def store(message):
            MyDatabase.save(message)

        count = manager.backfill_history(days=3, callback=store)
        print(f"Backfilled {count} messages")
    """
    import time

    print(f"📥 Backfilling message history (last {days} days)...")

    cutoff_time = int(time.time()) - (days * 24 * 60 * 60)
    total_fetched = 0
    before_id = None

    while total_fetched < max_messages:
        batch_size = min(100, max_messages - total_fetched)
        messages = self.fetch_history(limit=batch_size, before_id=before_id)

        if not messages:
            break

        # Filter messages within time window
        recent_messages = [
            msg for msg in messages
            if msg.created_at >= cutoff_time
        ]

        # Call callback for each message
        if callback:
            for msg in recent_messages:
                try:
                    callback(msg)
                except Exception as e:
                    print(f"⚠ Error in backfill callback: {e}")

        total_fetched += len(recent_messages)

        # Stop if we've gone past the cutoff
        if messages[-1].created_at < cutoff_time:
            break

        before_id = messages[-1].id
        print(f"  Fetched {total_fetched} messages...")

    print(f"✓ Backfill complete: {total_fetched} messages")
    return total_fetched
```

#### Step 1.4.4: Write tests

**Create:** `tests/unit/test_history.py`

**Tests to write:**
- `test_get_messages()` - Fetch messages (mocked)
- `test_get_messages_pagination()` - Pagination with before_id
- `test_fetch_history()` - Returns Message objects
- `test_backfill_history()` - Backfill with callback

**Create:** `tests/integration/test_history_live.py`

**Integration tests to write:**
- `test_fetch_real_history()` - Fetch from real API
- `test_pagination()` - Real pagination

**Run tests:**
```bash
pytest tests/unit/test_history.py -v
pytest -m integration tests/integration/test_history_live.py -v
```

**Acceptance Criteria:**
- ✅ `get_messages()` calls API correctly
- ✅ Pagination works with before_id
- ✅ `fetch_history()` returns Message objects
- ✅ `backfill_history()` fetches within time window
- ✅ Callback called for each message
- ✅ All tests pass

---

### Task 1.5: Remove Built-in Storage (1 day)

**Files to delete:**
- `group_py/storage.py`

**Files to modify:**
- `group_py/bot.py`
- `group_py/__init__.py`
- `pyproject.toml`

**Tests to delete:**
- `tests/test_storage.py`

**Implementation Steps:**

#### Step 1.5.1: Delete storage.py

**Delete file:**
```bash
git rm group_py/storage.py
```

#### Step 1.5.2: Remove storage from bot.py

**Location:** `group_py/bot.py`

**Remove from imports:**
```python
# DELETE this line:
from .storage import MessageStorage
```

**Remove from `__init__()` parameters:**
```python
# DELETE these parameters:
enable_storage: bool = False,
storage_connection: str = None,
```

**Remove from `__init__()` body:**
```python
# DELETE this entire block:
# Storage setup
self.storage: Optional[MessageStorage] = None
self.db_connection_string: Optional[str] = None
if enable_storage:
    if storage_connection:
        self.db_connection_string = storage_connection
    else:
        self.db_connection_string = "sqlite:///messages.db"
    self.storage = MessageStorage(self.db_connection_string)
```

**Remove methods:**
```python
# DELETE these methods:
def get_db_session(self):
def get_recent_messages(self, limit: int = 50, as_objects: bool = False):
```

**Remove storage calls from `process_webhook()`:**
```python
# DELETE:
if self.storage:
    try:
        self.storage.save_received(data)
    except Exception as e:
        print(f"⚠ Failed to store message: {e}")
```

**Remove storage calls from `send_message()`:**
```python
# DELETE:
if self.storage and self.group_id:
    try:
        self.storage.save_sent(text, self.group_id, self.bot_id, image_url)
    except Exception as e:
        print(f"⚠ Failed to store sent message: {e}")
```

#### Step 1.5.3: Remove storage exports from __init__.py

**Location:** `group_py/__init__.py`

**Remove:**
```python
# DELETE these imports:
from .storage import MessageStorage, StoredMessage
```

**Remove from `__all__`:**
```python
__all__ = [
    "GroupMeBotManager",
    "GroupMeBot",
    "Message",
    "GroupMeClient",
    # DELETE: "MessageStorage",
    # DELETE: "StoredMessage",
    # ... rest
]
```

#### Step 1.5.4: Remove SQLAlchemy dependency

**Location:** `pyproject.toml`

**Remove:**
```toml
dependencies = [
    "requests>=2.31.0",
    "python-dotenv>=1.0.0",
    # DELETE: "sqlalchemy>=2.0.0",
    "pyyaml>=6.0.0",
]
```

#### Step 1.5.5: Delete storage tests

**Delete file:**
```bash
git rm tests/test_storage.py
```

#### Step 1.5.6: Update examples to use @on_any_message for storage

**Modify:** All examples in `examples/`

**Replace storage usage:**
```python
# OLD (v2.0):
manager = GroupMeBotManager(
    enable_storage=True,
    storage_connection="sqlite:///messages.db"
)

# NEW (v3.0):
manager = GroupMeBotManager()

@manager.on_any_message
def store_message(message):
    # User implements their own storage
    # Example: MyDatabase.save(message)
    pass
```

**Run tests:**
```bash
pytest -m "not integration"  # All unit tests should pass
```

**Acceptance Criteria:**
- ✅ `storage.py` deleted
- ✅ All storage references removed from bot.py
- ✅ Storage exports removed from __init__.py
- ✅ SQLAlchemy dependency removed
- ✅ Storage tests deleted
- ✅ Examples updated to use @on_any_message
- ✅ All remaining tests pass

---

## Verification Checklist

Before moving to Phase 2, verify:

### Code Quality
- [ ] All new code has type hints
- [ ] All new code has docstrings
- [ ] Code follows existing style (run `black .`)
- [ ] No unused imports

### Testing
- [ ] All unit tests pass: `pytest -m "not integration"`
- [ ] Test coverage maintained: `pytest --cov=group_py`
- [ ] Integration tests pass (if applicable): `pytest -m integration`

### Features
- [ ] Mentions work with auto-calculated loci
- [ ] YAML config loads correctly
- [ ] `@on_any_message` fires for all messages
- [ ] History fetching works with pagination
- [ ] Built-in storage completely removed

### Documentation
- [ ] All new functions have docstrings with examples
- [ ] Examples updated to show new features
- [ ] No references to old storage system remain

### Git
- [ ] All changes committed
- [ ] Meaningful commit messages
- [ ] Branch is `v3-realtime`

**Final verification command:**
```bash
# Run full test suite
pytest -v

# Check code style
black --check .

# Verify dependencies
pip list | grep -E "pyyaml|sqlalchemy"
# Should show pyyaml, should NOT show sqlalchemy
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'yaml'"

**Solution:** Install pyyaml:
```bash
pip install pyyaml>=6.0.0
```

### "AttributeError: 'GroupMeBotManager' object has no attribute 'storage'"

**Solution:** This is expected! Storage was removed. Use `@on_any_message` instead.

### Tests failing after storage removal

**Solution:** Ensure all storage-related tests are deleted and remaining tests don't reference storage.

---

## Next Steps

Once Phase 1 is complete and verified:

1. **Review changes:**
   ```bash
   git diff main..v3-realtime
   ```

2. **Commit Phase 1:**
   ```bash
   git add .
   git commit -m "Phase 1: Foundation complete

   - Add mentions support with auto-calculated loci
   - Add YAML configuration loader
   - Add @on_any_message global handler
   - Add history fetching from API
   - Remove built-in storage (breaking change)
   - Remove SQLAlchemy dependency"
   ```

3. **Proceed to Phase 2:** [PHASE_2_REALTIME.md](./PHASE_2_REALTIME.md)

---

## Estimated Timeline

| Task | Duration | Dependencies |
|------|----------|--------------|
| 1.1 Mentions | 2 days | None |
| 1.2 YAML Config | 2 days | None |
| 1.3 Global Handler | 1 day | None |
| 1.4 History Fetching | 1 day | None |
| 1.5 Remove Storage | 1 day | Tasks 1.1-1.4 |

**Total: 5-7 days (1 week)**

Tasks 1.1-1.4 can be done in parallel by multiple developers, but 1.5 should wait until others are complete.

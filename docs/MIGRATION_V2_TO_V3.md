# Migration Guide: v2.x to v3.0

This guide helps you migrate your group-py bot from v2.x to v3.0.

## Overview of Changes

v3.0 brings major improvements:
- **Real-time WebSocket support** - No webhook server needed
- **YAML configuration** - Cleaner credential management
- **Built-in @mentions** - Automatic loci calculation
- **Global message handlers** - `@on_any_message` for logging/storage
- **History fetching** - Pull message history from API
- **Optional Django models** - Pre-built message storage

### Breaking Changes

1. **Removed built-in storage** - Implement with `@on_any_message`
2. **Deprecated `message.reply()`** - Use `message.post()` instead

---

## Step-by-Step Migration

### Step 1: Update Dependencies

```bash
pip install --upgrade group-py
```

If you want Django model support:
```bash
pip install group-py[django]
```

### Step 2: Replace reply() with post()

`message.reply()` is deprecated and will be removed in v4.0.

**Before (v2.x):**
```python
@manager.command("hello")
def hello(message, args):
    message.reply(f"Hello, {message.name}!")
```

**After (v3.0):**
```python
@manager.command("hello")
def hello(message, args):
    message.post(f"Hello, {message.name}!")
```

The `post()` method works identically - it's just a clearer name since you're posting to the group, not always replying.

### Step 3: Implement Your Own Storage (if needed)

v3.0 removes built-in storage. Instead, use `@on_any_message`:

**Before (v2.x):**
```python
# Built-in storage handled automatically
manager = GroupMeBotManager(
    ...,
    storage=SQLAlchemyStorage(...)
)
```

**After (v3.0):**
```python
from your_app.models import Message as DBMessage

manager = GroupMeBotManager(...)

@manager.on_any_message
def store_message(message):
    # Save to your database
    DBMessage.objects.create(
        message_id=message.id,
        text=message.text,
        user_id=message.user_id,
        group_id=message.group_id,
        created_at=message.created_at,
    )
```

**Why this change?**
- Simpler library with fewer dependencies
- You control the storage format
- Works with any database (Django, SQLAlchemy, MongoDB, etc.)
- Optional Django models available for convenience

### Step 4: Consider Using YAML Configuration

v3.0 supports YAML configuration files for cleaner setup:

**Before (v2.x):**
```python
manager = GroupMeBotManager(
    api_key="hardcoded_key",
    group_id="12345",
    callback_url="https://...",
)
```

**After (v3.0):**
```python
# Option 1: Auto-load from groupme_config.yaml
manager = GroupMeBotManager()

# Option 2: Specify config file
manager = GroupMeBotManager.from_yaml("bots.yaml")
```

**groupme_config.yaml:**
```yaml
api_key: "your_api_key"
group_id: "12345"
callback_url: "https://..."
bot_name: "MyBot"
```

### Step 5: Consider Real-time Mode

v3.0 supports WebSocket connections - no webhook server needed!

**Before (v2.x):**
```python
# Required: Flask/Django server + webhook endpoint
from flask import Flask
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    manager.process_webhook(request.get_json())
    return "ok"

app.run()
```

**After (v3.0) - Real-time mode:**
```python
# No server needed!
manager = GroupMeBotManager(
    api_key="...",
    group_id="...",
    user_id="...",        # Required for realtime
    enable_realtime=True,
)

# Bot receives messages via WebSocket automatically
import time
while True:
    time.sleep(1)
```

---

## New Features to Try

### @mentions Support

v3.0 has built-in @mentions with automatic loci calculation:

```python
@manager.command("tag")
def tag_user(message, args):
    message.post(
        f"Hey @{args}, check this out!",
        mentions=[{"user_id": "12345", "name": args}]
    )
```

### Global Message Handler

Process ALL messages before command routing:

```python
@manager.on_any_message
def log_all(message):
    print(f"[{message.name}]: {message.text}")

@manager.on_any_message
def count_messages(message):
    stats.increment("messages_received")
```

### History Fetching

Pull historical messages on startup:

```python
# Fetch recent messages
messages = manager.fetch_history(limit=50)

# Backfill with callback
def store(msg):
    MyDatabase.save(msg)

manager.backfill_history(days=7, callback=store)
```

### Optional Django Models

Pre-built Django models for message storage:

```python
# settings.py
INSTALLED_APPS = [
    ...
    'group_py.contrib.django',
]

# your_app/views.py
from group_py.contrib.django.models import GroupMeMessage

@manager.on_any_message
def store(message):
    GroupMeMessage.from_message(message).save()
```

---

## Troubleshooting

### DeprecationWarning for reply()

This is expected! Update your code to use `post()` instead:
```python
# Old (shows warning)
message.reply("text")

# New (no warning)
message.post("text")
```

### Storage not working

v3.0 removed built-in storage. Use `@on_any_message`:
```python
@manager.on_any_message
def store(message):
    # Your storage code here
    pass
```

### Import errors

Some imports have changed:
```python
# v2.x
from group_py.storage import SQLAlchemyStorage  # Removed

# v3.0
from group_py.contrib.django.models import GroupMeMessage  # New optional
```

### Real-time mode not connecting

Ensure you have:
1. `user_id` set (required for WebSocket)
2. `enable_realtime=True`
3. Valid API key with access to the group

---

## Quick Reference

| v2.x | v3.0 |
|------|------|
| `message.reply()` | `message.post()` |
| `SQLAlchemyStorage` | Use `@on_any_message` |
| Environment variables only | YAML config supported |
| Webhook only | WebSocket + Webhook |
| No mentions support | Built-in mentions |
| No history fetching | `fetch_history()` / `backfill_history()` |

---

## Need Help?

- [GitHub Issues](https://github.com/mfaircloth/group-py/issues)
- See `examples/` for working code
- Check the [README](../README.md) for quick start guide

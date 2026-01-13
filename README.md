# group-py

A modern Python framework for building GroupMe bots with real-time WebSocket support, command routing, and flexible message handling.

## Features

- **Real-time WebSocket** - Receive messages instantly without webhooks
- **Command Routing** - Decorator-based command handlers
- **YAML Configuration** - Clean credential management
- **@Mentions Support** - Automatic loci calculation
- **History Fetching** - Pull and backfill message history
- **Optional Django Models** - Pre-built message storage
- **Bot Recovery** - Auto-reuse existing bots on restart

## Installation

```bash
pip install group-py
```

With Django support:
```bash
pip install group-py[django]
```

## Quick Start

### Real-time Bot (No Webhook Needed!)

```python
from group_py import GroupMeBotManager

manager = GroupMeBotManager(
    api_key="your_api_key",
    group_id="your_group_id",
    user_id="your_user_id",
    enable_realtime=True,
)

@manager.command("hello")
def hello(message, args):
    message.post(f"Hello, {message.name}!")

@manager.command("echo")
def echo(message, args):
    message.post(args)

# Keep running
import time
while True:
    time.sleep(1)
```

### Webhook Bot (Flask)

```python
from flask import Flask, request
from group_py import GroupMeBotManager

app = Flask(__name__)
manager = GroupMeBotManager(
    api_key="your_api_key",
    group_id="your_group_id",
)

@manager.command("ping")
def ping(message, args):
    message.post("Pong!")

@app.route("/webhook", methods=["POST"])
def webhook():
    manager.process_webhook(request.get_json())
    return "ok"

if __name__ == "__main__":
    app.run()
```

## Configuration

### YAML Config (Recommended)

Create `groupme_config.yaml`:

```yaml
api_key: "your_api_key"
group_id: "your_group_id"
user_id: "your_user_id"
bot_name: "MyBot"

realtime:
  enabled: true
```

Then load automatically:

```python
# Auto-loads groupme_config.yaml
manager = GroupMeBotManager()

# Or specify path
manager = GroupMeBotManager.from_yaml("custom_config.yaml")
```

### Environment Variables

```bash
export GROUPME_API_KEY="your_api_key"
export GROUPME_GROUP_ID="your_group_id"
export GROUPME_USER_ID="your_user_id"
```

```python
manager = GroupMeBotManager()  # Uses env vars
```

## Core Concepts

### Commands

```python
@manager.command("help")
def help_cmd(message, args):
    message.post("Available commands: help, ping, echo")

@manager.command("echo")
def echo(message, args):
    if args:
        message.post(args)
    else:
        message.post("Usage: echo <text>")
```

### Async Commands

For long-running operations:

```python
@manager.async_command("generate", ack_message="Generating...")
def generate(message, args):
    import time
    time.sleep(5)  # Simulate work
    message.post(f"Generated: {args}")
```

### Global Message Handler

Runs for ALL messages before command routing:

```python
@manager.on_any_message
def log_all(message):
    print(f"[{message.name}]: {message.text}")

@manager.on_any_message
def store_all(message):
    MyDatabase.save(message)
```

### @Mentions

Automatic loci calculation for mentions:

```python
@manager.command("tag")
def tag(message, args):
    message.post(
        f"Hey @{message.name}!",
        mentions=[{
            "user_id": message.user_id,
            "name": message.name
        }]
    )
```

### History Fetching

```python
# Fetch recent messages
messages = manager.fetch_history(limit=50)

# Backfill with callback
def store(msg):
    MyDatabase.save(msg)

count = manager.backfill_history(days=7, callback=store)
print(f"Stored {count} messages")
```

## Django Integration

### Setup

1. Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    'group_py.contrib.django',
]
```

2. Run migrations:

```bash
python manage.py migrate
```

### Usage

```python
from group_py.contrib.django.models import GroupMeMessage

@manager.on_any_message
def store(message):
    GroupMeMessage.from_message(message).save()

# Query messages
recent = GroupMeMessage.objects.filter(
    group_id="12345"
).order_by('-created_at')[:10]

# Convert back to Message objects
messages = [msg.to_message() for msg in recent]
```

## API Reference

### GroupMeBotManager

```python
manager = GroupMeBotManager(
    api_key="...",           # GroupMe API key
    group_id="...",          # Group ID to operate in
    callback_url="...",      # Webhook URL (optional)
    bot_name="System",       # Primary bot name
    bot_id="...",            # Existing bot ID (optional)
    user_id="...",           # User ID (required for realtime)
    enable_realtime=False,   # Enable WebSocket
    config_file="...",       # YAML config path
)
```

### Decorators

```python
@manager.command("prefix")          # Command handler
@manager.async_command("prefix")    # Async command
@manager.on_message                 # Non-command messages
@manager.on_any_message             # ALL messages (preprocessor)
@manager.on_unknown_command         # Unknown commands
```

### Message Object

```python
message.id            # Message ID
message.text          # Message text
message.user_id       # Sender's user ID
message.name          # Sender's display name
message.group_id      # Group ID
message.created_at    # Unix timestamp
message.attachments   # List of attachments

message.post(text, **kwargs)  # Send message to group
message.has_image()           # Check for image attachment
message.get_image_url()       # Get image URL
```

## Examples

See the `examples/` directory:

- `realtime_bot.py` - Real-time WebSocket bot
- `yaml_config_bot.py` - YAML configuration
- `mentions_bot.py` - @mentions support
- `django_storage.py` - Django integration

## Migration from v2.x

See [Migration Guide](docs/MIGRATION_V2_TO_V3.md) for upgrading from v2.x.

Key changes:
- Use `message.post()` instead of `message.reply()` (deprecated)
- Use `@on_any_message` for storage (built-in storage removed)
- New features: realtime, YAML config, mentions, history

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Run with coverage
pytest --cov=group_py
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

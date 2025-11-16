# GroupMe Bot Framework

A simplified Python framework for building GroupMe bots with command routing, async support, and message storage.

## Features

✅ **Simple Setup** - Minimal configuration with environment variables
✅ **Command Routing** - Decorator-based command handlers
✅ **Async Commands** - Automatic threading for long-running operations
✅ **Message Storage** - SQLAlchemy-based storage (SQLite, PostgreSQL, MySQL)
✅ **Multi-Bot Support** - Run multiple bots in one application
✅ **Rich Media** - Send images and locations
✅ **Framework Agnostic** - Works with Flask, Django, FastAPI, or any web framework
✅ **Type Hints** - Full type annotations throughout

## Installation

```bash
pip install groupme-bot
```

Or install from source:

```bash
git clone https://github.com/mfaircloth/group-py.git
cd group-py
pip install -e .
```


## Quick Start

```python
from groupme_bot import GroupMeBot

# Initialize bot (auto-creates if needed)
bot = GroupMeBot(
    group_id="your_group_id",
    callback_url="https://yourserver.com/webhook",
    enable_storage=True
)

# Register a command
@bot.command("/hello")
def hello(message, args):
    message.reply(f"Hi {message.name}!")

# In your Flask/Django view:
@app.route('/webhook', methods=['POST'])
def webhook():
    bot.process_message(request.get_json())
    return "ok", 200
```

## Getting Started

### 1. Get Your API Key

1. Go to [GroupMe Developer Portal](https://dev.groupme.com/)
2. Sign in with your GroupMe account
3. Your API key is at the top right by your username

### 2. Find Your Group ID

```python
from groupme_bot import GroupMeBot

bot = GroupMeBot(api_key="your_api_key")
groups = bot.list_groups()

for group in groups:
    print(f"{group['name']}: {group['id']}")
```

### 3. Set Up Environment Variables

Create a `.env` file:

```bash
GROUPME_API_KEY=your_api_key_here
GROUPME_GROUP_ID=your_group_id_here
GROUPME_CALLBACK_URL=https://yourserver.com/webhook
```

### 4. Set Up Webhook (for local development)

Use [ngrok](https://ngrok.com/) to expose your local server:

```bash
ngrok http 3000
# Use the HTTPS URL as your callback_url
```


## Core Concepts

### Command Routing

Commands are registered using decorators and automatically route messages to handlers:

```python
from groupme_bot import GroupMeBot

bot = GroupMeBot()

# Simple command
@bot.command("/hello")
def hello_command(message, args):
    """args contains everything after '/hello'"""
    message.reply(f"Hello {message.name}!")

# Command with arguments
@bot.command("/echo")
def echo_command(message, args):
    message.reply(f"You said: {args}")
```

### Async Commands

For long-running operations, use async commands that run in background threads:

```python
@bot.async_command("/prompt", ack_message="🤔 Thinking...")
def handle_prompt(message, args):
    """This runs in a background thread"""
    import time
    time.sleep(5)  # Long operation

    # Get conversation context
    context = bot.get_recent_messages(limit=20, as_objects=True)

    # Process with LLM, etc.
    result = process_with_llm(args, context)
    message.reply(result)
```

The bot immediately sends the acknowledgment message, then processes the command in the background.

### Message Handlers

Handle all messages that don't match commands:

```python
@bot.on_message
def handle_message(message):
    """Called for non-command messages"""
    if "hello" in message.text.lower():
        message.reply("Hi there!")

    # Check for attachments
    if message.has_image():
        message.reply("Nice image!")
```

### Unknown Commands

Handle unrecognized commands:

```python
@bot.on_unknown_command
def handle_unknown(message, command_text):
    message.reply(f"Unknown command: {command_text}\nTry /help")
```

### Message Storage

Enable SQLAlchemy-based storage to save and query message history:

```python
bot = GroupMeBot(
    enable_storage=True,
    storage_connection="sqlite:///messages.db"  # or PostgreSQL, MySQL
)

# Get recent messages
messages = bot.get_recent_messages(limit=50, as_objects=True)
for msg in messages:
    print(f"{msg.name}: {msg.text}")

# Custom queries with SQLAlchemy
from groupme_bot.storage import StoredMessage

session = bot.get_db_session()
try:
    results = session.query(StoredMessage)\
        .filter(StoredMessage.text.like('%pizza%'))\
        .order_by(StoredMessage.created_at.desc())\
        .limit(10)\
        .all()

    from groupme_bot import Message
    messages = Message.from_query_results(results)
finally:
    session.close()
```


## API Reference

### GroupMeBot

Main bot class for handling webhooks and sending messages.

#### Constructor

```python
bot = GroupMeBot(
    api_key=None,              # Or set GROUPME_API_KEY env var
    bot_id=None,               # Or set GROUPME_BOT_ID env var
    group_id=None,             # Or set GROUPME_GROUP_ID env var
    callback_url=None,         # Or set GROUPME_CALLBACK_URL env var
    bot_name="Bot",            # Name for auto-created bot
    avatar_url=None,           # Avatar for auto-created bot
    auto_create=True,          # Auto-create bot if bot_id not provided
    enable_storage=False,      # Enable message storage
    storage_connection=None    # Custom DB connection string
)
```

#### Methods

- **`@bot.on_message`** - Decorator to register message handler
- **`@bot.command(prefix)`** - Decorator to register command handler
- **`@bot.async_command(prefix, ack_message=None)`** - Decorator for async command
- **`@bot.on_unknown_command`** - Decorator for unknown command handler
- **`bot.process_message(data)`** - Process webhook payload (call from your web framework)
- **`bot.send_message(text, image_url=None, **kwargs)`** - Send a message
- **`bot.send_location(name, lat, lng, text="")`** - Send a location
- **`bot.list_groups()`** - List all groups (helpful for finding group_id)
- **`bot.get_db_session()`** - Get SQLAlchemy session for custom queries
- **`bot.get_recent_messages(limit=50, as_objects=False)`** - Get recent messages
- **`bot.destroy()`** - Manually destroy auto-created bot

### GroupMeSender

Lightweight send-only bot (no webhook handling).

```python
from groupme_bot import GroupMeSender

sender = GroupMeSender(
    bot_id="your_bot_id",
    api_key="your_api_key"
)

sender.send_message("Hello!")
sender.send_location("Office", 37.7749, -122.4194)
```

### Message

Message object passed to handlers.

#### Properties

- `message.id` - Message ID
- `message.text` - Message text (can be None)
- `message.user_id` - Sender user ID
- `message.name` - Sender name
- `message.group_id` - Group ID
- `message.created_at` - Unix timestamp
- `message.system` - Boolean, system message
- `message.sender_type` - "user" or "bot"
- `message.avatar_url` - Sender avatar URL
- `message.attachments` - List of attachments

#### Methods

- `message.reply(text, **kwargs)` - Reply to message
- `message.has_image()` - Check for image attachment
- `message.get_image_url()` - Get first image URL
- `message.has_location()` - Check for location attachment
- `message.get_location()` - Get (lat, lng, name) tuple


## Integration Examples

### Flask

```python
from flask import Flask, request
from groupme_bot import GroupMeBot

app = Flask(__name__)
bot = GroupMeBot(enable_storage=True)

@bot.command("/hello")
def hello(message, args):
    message.reply(f"Hi {message.name}!")

@app.route('/webhook', methods=['POST'])
def webhook():
    bot.process_message(request.get_json())
    return "ok", 200

if __name__ == "__main__":
    app.run(port=3000)
```

### Django

```python
# bot_instance.py
from groupme_bot import GroupMeBot
from django.conf import settings

# Use Django's database
db = settings.DATABASES['default']
connection = f"postgresql://{db['USER']}:{db['PASSWORD']}@{db['HOST']}/{db['NAME']}"

bot = GroupMeBot(
    enable_storage=True,
    storage_connection=connection
)

@bot.command("/echo")
def echo(message, args):
    message.reply(f"You said: {args}")

# views.py
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from .bot_instance import bot

@method_decorator(csrf_exempt, name='dispatch')
class GroupMeWebhook(View):
    def post(self, request):
        bot.process_message(json.loads(request.body))
        return JsonResponse({"ok": True})
```

### Multiple Bots

```python
from groupme_bot import GroupMeBot, GroupMeSender

# Main bot handles webhooks
system_bot = GroupMeBot(
    group_id="your_group_id",
    callback_url="https://yourserver.com/webhook",
    enable_storage=True
)

# Secondary bot only sends messages
bean_bot = GroupMeSender(
    bot_id="bean_bot_id",
    api_key="your_api_key"
)

@system_bot.command("/bean")
def bean_command(message, args):
    bean_bot.send_message(f"🫘 {args}")

@system_bot.on_message
def handle_images(message):
    if message.has_image():
        bean_bot.send_message("Nice pic!")
```

## Database Support

The framework supports any SQLAlchemy-compatible database:

### SQLite (Default)

```python
bot = GroupMeBot(enable_storage=True)
# Uses sqlite:///messages.db
```

### PostgreSQL

```python
bot = GroupMeBot(
    enable_storage=True,
    storage_connection="postgresql://user:pass@localhost/dbname"
)
```

### MySQL

```python
bot = GroupMeBot(
    enable_storage=True,
    storage_connection="mysql://user:pass@localhost/dbname"
)
```

### Custom Queries

```python
from groupme_bot.storage import StoredMessage
from sqlalchemy import func

session = bot.get_db_session()
try:
    # Count messages by user
    results = session.query(
        StoredMessage.user_id,
        func.count(StoredMessage.id)
    ).group_by(StoredMessage.user_id).all()

    # Search with full-text
    messages = session.query(StoredMessage)\
        .filter(StoredMessage.text.like('%pizza%'))\
        .order_by(StoredMessage.created_at.desc())\
        .limit(10)\
        .all()
finally:
    session.close()
```

## Advanced Features

### Rich Media

Send images and locations:

```python
# Send image
bot.send_message("Check this out!", image_url="https://example.com/image.jpg")

# Send location
bot.send_location("Office", lat=37.7749, lng=-122.4194, text="Meet here!")

# Check for attachments in messages
@bot.on_message
def handle_media(message):
    if message.has_image():
        url = message.get_image_url()
        message.reply(f"Nice image: {url}")

    if message.has_location():
        lat, lng, name = message.get_location()
        message.reply(f"Location: {name} ({lat}, {lng})")
```

### Auto-Create and Cleanup

Bots can be automatically created and destroyed:

```python
# Auto-creates bot on initialization
bot = GroupMeBot(
    group_id="your_group_id",
    callback_url="https://yourserver.com/webhook",
    bot_name="My Bot",
    auto_create=True  # Default
)

# Bot is automatically destroyed when program exits
# Or manually destroy:
bot.destroy()
```

### Environment Variables

All configuration can be set via environment variables:

```bash
export GROUPME_API_KEY=your_api_key
export GROUPME_BOT_ID=your_bot_id
export GROUPME_GROUP_ID=your_group_id
export GROUPME_CALLBACK_URL=https://yourserver.com/webhook
```

```python
# No arguments needed!
bot = GroupMeBot()
```

## Troubleshooting

### Bot not responding

- Check that your callback URL is publicly accessible
- Verify the webhook is registered in GroupMe
- Check that you're calling `bot.process_message(data)` in your webhook handler

### Messages not storing

- Ensure `enable_storage=True` when initializing the bot
- Check database connection string is valid
- Verify database permissions

### Auto-create not working

- Ensure `group_id` and `callback_url` are provided
- Check API key has permissions to create bots
- Verify callback URL is publicly accessible

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.

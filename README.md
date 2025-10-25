# group-py
Groupme API Handler

## Purpose
This module is to be used to simplify interactions with the GroupMe API.


### Authentication
Groupme API can be accessed with the Users API Token.
[See the Groupme Developers documenation](https://dev.groupme.com/). The API token can be found at the top right by your username. 

All of these commands assume the user has the required permissions for their groups.

The access token can be set using the `GROUPME_API_TOKEN` environment variable.


### Message Router

The message router allows you to handle GroupMe messages by routing them to appropriate handlers based on custom logic. Handlers receive a `HandlerContext` containing the bot, router, and message, allowing them to post responses and access other handlers.

#### Basic Usage with CommandHandler

For simple command-based handlers, use `CommandHandler` which automatically handles command matching:

``` py
from group_py import CommandHandler, MessageRouter, HandlerContext

class ReadyHandler(CommandHandler):
    command_str = '!ready'  # Define the command once

    @staticmethod
    def help():
        return 'Responds when users are ready.'

    @staticmethod
    def execute(context: HandlerContext) -> None:
        '''Executes when !ready command is received.'''
        context.bot.post_message(f'{context.message.name} is ready!')

# Create router with handlers and bot
bot = GroupMeBot(bot_id='your_bot_id')
router = MessageRouter([ReadyHandler], bot=bot)
```

#### Advanced: Custom Message Matching

For more complex matching logic, override `can_handle()`:

``` py
from group_py import CommandHandler, MessageRouter, HandlerContext

class PingHandler(CommandHandler):
    command_str = '!ping'

    @staticmethod
    def help():
        return 'Responds with pong.'

    @classmethod
    def can_handle(cls, message):
        # Custom logic: match command or respond to mentions
        return (message.text.lower().strip() == cls.command_str or
                'ping' in message.text.lower())

    @staticmethod
    def execute(context: HandlerContext) -> None:
        context.bot.post_message('Pong!')

router = MessageRouter([PingHandler], bot=bot)
```

#### Using HandlerContext

The `HandlerContext` passed to `execute()` provides access to:
- `context.bot` - The GroupMeBot instance for posting messages
- `context.router` - The MessageRouter for accessing other handlers
- `context.message` - The Message object with sender info, text, etc.

``` py
class InfoHandler(CommandHandler):
    command_str = '!info'

    @staticmethod
    def help():
        return 'Shows available commands.'

    @staticmethod
    def execute(context: HandlerContext) -> None:
        # Access message details
        sender = context.message.name

        # Get all available commands from router
        commands = []
        for route in context.router.get_routes.values():
            if hasattr(route.handler, 'command_str'):
                cmd = route.handler.command_str
                help_text = route.handler.help()
                commands.append(f'{cmd}: {help_text}')

        # Post response
        response = f'Hi {sender}!\n' + '\n'.join(commands)
        context.bot.post_message(response)

router = MessageRouter([InfoHandler], bot=bot)
```

#### Flask Integration Example

``` py
from flask import Flask, request
from group_py import MessageRouter, Message, GroupMeBot

app = Flask(__name__)

# Initialize bot and router
bot = GroupMeBot(bot_id='your_bot_id')
router = MessageRouter([ReadyHandler, PingHandler], bot=bot)

@app.route('/callback', methods=['POST'])
def callback():
    raw_message_data = request.get_json()
    message = Message(raw_message_data)
    result = router.route(message)
    return result
```


### Bots

Bots can be created, managed, and used to post messages to GroupMe groups.

#### Creating a New Bot

``` py
from group_py import GroupMeBot

bot = GroupMeBot(
    name='my_awesome_bot',
    group_id='1234567890',
    avatar_url='https://i.groupme.com/123456789',
    callback_url='https://example.com/bots/callback'
)

# Create the bot in the group
bot_details = bot.create()
print(bot_details)
# {
#   'bot_id': '1234567890',
#   'group_id': '1234567890',
#   'name': 'my_awesome_bot',
#   'avatar_url': 'https://i.groupme.com/123456789',
#   'callback_url': 'https://example.com/bots/callback',
#   'dm_notification': False,
#   'active': True
# }
```

#### Using an Existing Bot

If you already have a bot ID, you can load it directly:

``` py
from group_py import GroupMeBot

# Load existing bot by ID
bot = GroupMeBot(bot_id='1234567890')

# Post a message
bot.post_message('Hello from my bot!')

# Post a message with an image
bot.post_message('Check this out!', picture_url='https://example.com/image.jpg')
```

#### Finding and Reusing Bots

The bot will automatically search for existing bots by name and group:

``` py
from group_py import GroupMeBot

# This will search for an existing bot with this name in the group
# If found, it will use that bot. If not found, it will raise an error.
bot = GroupMeBot(
    name='my_awesome_bot',
    group_id='1234567890',
    search_for_existing=True  # Default is True
)

bot.post_message('Reusing existing bot!')
```

#### Cleaning Up

``` py
# Destroy the bot and remove it from the group
bot.destroy()
```

#### Singleton Pattern

`GroupMeBot` uses a singleton pattern, so you only have one instance per bot:

``` py
from group_py import GroupMeBot

bot1 = GroupMeBot(bot_id='1234567890')
bot2 = GroupMeBot(bot_id='1234567890')

assert bot1 is bot2  # Same instance!
```


## Complete Examples

### Example 1: Simple Echo Bot

A bot that echoes messages back to the group:

``` py
from group_py import CommandHandler, MessageRouter, HandlerContext, GroupMeBot, Message

class EchoHandler(CommandHandler):
    command_str = '!echo'

    @staticmethod
    def help():
        return 'Echoes your message back. Usage: !echo <message>'

    @classmethod
    def can_handle(cls, message: Message):
        return message.text.lower().strip().startswith(cls.command_str)

    @staticmethod
    def execute(context: HandlerContext) -> None:
        # Extract the message after the command
        text = context.message.text[len('!echo'):].strip()
        if text:
            context.bot.post_message(f'Echo: {text}')
        else:
            context.bot.post_message('Usage: !echo <message>')

# Setup
bot = GroupMeBot(bot_id='your_bot_id')
router = MessageRouter([EchoHandler], bot=bot)
```

### Example 2: Dice Roller

A bot that rolls dice:

``` py
import random
from group_py import CommandHandler, MessageRouter, HandlerContext, GroupMeBot, Message

class DiceHandler(CommandHandler):
    command_str = '!roll'

    @staticmethod
    def help():
        return 'Rolls a dice. Usage: !roll [sides] (default: 6)'

    @classmethod
    def can_handle(cls, message: Message):
        return message.text.lower().strip().startswith(cls.command_str)

    @staticmethod
    def execute(context: HandlerContext) -> None:
        text = context.message.text[len('!roll'):].strip()

        try:
            sides = int(text) if text else 6
            if sides < 1:
                context.bot.post_message('Dice must have at least 1 side!')
                return

            roll = random.randint(1, sides)
            context.bot.post_message(
                f'{context.message.name} rolled a {sides}-sided dice: **{roll}**'
            )
        except ValueError:
            context.bot.post_message('Invalid number of sides!')

# Setup
bot = GroupMeBot(bot_id='your_bot_id')
router = MessageRouter([DiceHandler], bot=bot)
```

### Example 3: Multi-Handler Bot with Help

A bot with multiple commands and a help system:

``` py
from group_py import CommandHandler, MessageRouter, HandlerContext, GroupMeBot, Message

class GreetHandler(CommandHandler):
    command_str = '!greet'

    @staticmethod
    def help():
        return 'Greets you by name'

    @staticmethod
    def execute(context: HandlerContext) -> None:
        context.bot.post_message(f'Hello, {context.message.name}! 👋')

class TimeHandler(CommandHandler):
    command_str = '!time'

    @staticmethod
    def help():
        return 'Shows current time'

    @staticmethod
    def execute(context: HandlerContext) -> None:
        from datetime import datetime
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        context.bot.post_message(f'Current time: {current_time}')

class StatusHandler(CommandHandler):
    command_str = '!status'

    @staticmethod
    def help():
        return 'Shows bot status'

    @staticmethod
    def execute(context: HandlerContext) -> None:
        context.bot.post_message('🤖 Bot is online and ready!')

# Setup with multiple handlers
bot = GroupMeBot(bot_id='your_bot_id')
router = MessageRouter(
    [GreetHandler, TimeHandler, StatusHandler],
    bot=bot
)

# The router automatically includes a !help command that lists all handlers
```

### Example 4: Flask Server with Message Routing

A complete Flask server that handles GroupMe callbacks:

``` py
from flask import Flask, request
from group_py import (
    CommandHandler, MessageRouter, HandlerContext,
    GroupMeBot, Message
)

app = Flask(__name__)

# Define handlers
class PingHandler(CommandHandler):
    command_str = '!ping'

    @staticmethod
    def help():
        return 'Responds with pong'

    @staticmethod
    def execute(context: HandlerContext) -> None:
        context.bot.post_message('Pong! 🏓')

class QuoteHandler(CommandHandler):
    command_str = '!quote'

    @staticmethod
    def help():
        return 'Posts an inspirational quote'

    @staticmethod
    def execute(context: HandlerContext) -> None:
        quotes = [
            'The only way to do great work is to love what you do. - Steve Jobs',
            'Innovation distinguishes between a leader and a follower. - Steve Jobs',
            'Life is what happens when you\'re busy making other plans. - John Lennon',
        ]
        import random
        context.bot.post_message(random.choice(quotes))

# Initialize bot and router
bot = GroupMeBot(bot_id='your_bot_id')
router = MessageRouter([PingHandler, QuoteHandler], bot=bot)

@app.route('/callback', methods=['POST'])
def callback():
    '''Handle incoming GroupMe messages'''
    try:
        raw_message_data = request.get_json()

        # Ignore messages from the bot itself
        if raw_message_data.get('sender_type') == 'bot':
            return {'status': 'ok'}

        message = Message(raw_message_data)
        router.route(message)

        return {'status': 'ok'}
    except Exception as e:
        print(f'Error handling callback: {e}')
        return {'status': 'error'}, 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### Example 5: Handler with Router Access

A handler that accesses other handlers through the router:

``` py
from group_py import CommandHandler, MessageRouter, HandlerContext, GroupMeBot, Message

class ListCommandsHandler(CommandHandler):
    command_str = '!commands'

    @staticmethod
    def help():
        return 'Lists all available commands'

    @staticmethod
    def execute(context: HandlerContext) -> None:
        commands = []

        # Iterate through all handlers in the router
        for route in context.router.get_routes.values():
            handler = route.handler

            # Check if it's a CommandHandler
            if hasattr(handler, 'command_str') and handler.command_str:
                cmd = handler.command_str
                help_text = handler.help()
                commands.append(f'**{cmd}** - {help_text}')

        if commands:
            message = 'Available commands:\n' + '\n'.join(commands)
        else:
            message = 'No commands available'

        context.bot.post_message(message)

# Setup
bot = GroupMeBot(bot_id='your_bot_id')
router = MessageRouter([ListCommandsHandler], bot=bot)
```

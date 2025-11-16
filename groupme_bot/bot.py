"""Main GroupMe bot class with webhook handling and command routing."""

import os
import atexit
import threading
from typing import Callable, List, Optional, Dict, Any
from .client import GroupMeClient
from .models import Message
from .storage import MessageStorage
from .exceptions import ConfigurationError


class GroupMeBot:
    """
    Main bot class for handling GroupMe webhooks and sending messages.
    Supports command routing, async commands, and optional message storage.
    """

    def __init__(
        self,
        api_key: str = None,
        bot_id: str = None,
        group_id: str = None,
        callback_url: str = None,
        bot_name: str = "Bot",
        avatar_url: str = None,
        auto_create: bool = True,
        enable_storage: bool = False,
        storage_connection: str = None,
    ):
        """
        Initialize the bot with API credentials.
        Falls back to environment variables if not provided.

        Args:
            api_key: GroupMe API key (or set GROUPME_API_KEY env var)
            bot_id: Existing bot ID (or set GROUPME_BOT_ID env var)
            group_id: Group ID for bot creation (or set GROUPME_GROUP_ID env var)
            callback_url: Webhook callback URL (or set GROUPME_CALLBACK_URL env var)
            bot_name: Name for auto-created bot (default: "Bot")
            avatar_url: Avatar URL for auto-created bot
            auto_create: If True and no bot_id provided, create a bot automatically
            enable_storage: If True, enable SQLite message storage
            storage_connection: Custom DB path (e.g., "sqlite:///myapp.db")

        Raises:
            ConfigurationError: If required credentials are missing
        """
        # Load configuration
        self.api_key = api_key or os.getenv("GROUPME_API_KEY")
        self.bot_id = bot_id or os.getenv("GROUPME_BOT_ID")
        self.group_id = group_id or os.getenv("GROUPME_GROUP_ID")
        self.callback_url = callback_url or os.getenv("GROUPME_CALLBACK_URL")
        self.bot_name = bot_name
        self.avatar_url = avatar_url

        if not self.api_key:
            raise ConfigurationError(
                "API key required. Set GROUPME_API_KEY environment variable "
                "or pass api_key to __init__"
            )

        # Initialize client
        self.client = GroupMeClient(self.api_key, self.bot_id)

        # Handler storage
        self._handlers: List[Callable] = []
        self._commands: Dict[str, Callable] = {}
        self._async_commands: Dict[str, tuple] = {}  # command -> (handler, ack_message)
        self._unknown_command_handler: Optional[Callable] = None

        # Auto-create tracking
        self._auto_created = False

        # Storage setup
        self.storage: Optional[MessageStorage] = None
        self.db_connection_string: Optional[str] = None
        if enable_storage:
            if storage_connection:
                self.db_connection_string = storage_connection
            else:
                self.db_connection_string = "sqlite:///messages.db"
            self.storage = MessageStorage(self.db_connection_string)

        # Auto-create bot if needed
        if auto_create and not self.bot_id:
            if not self.group_id or not self.callback_url:
                raise ConfigurationError(
                    "To auto-create a bot, provide group_id and callback_url "
                    "(or set GROUPME_GROUP_ID and GROUPME_CALLBACK_URL env vars)"
                )
            self._create_bot()

        # Validate we have what we need
        if not self.bot_id:
            raise ConfigurationError("bot_id is required (or enable auto_create)")

        # Register cleanup on exit
        atexit.register(self._cleanup)

    def _create_bot(self):
        """Create a new bot and store its ID."""
        try:
            response = self.client.create_bot(
                name=self.bot_name,
                group_id=self.group_id,
                callback_url=self.callback_url,
                avatar_url=self.avatar_url,
            )
            self.bot_id = response["response"]["bot"]["bot_id"]
            self.client.bot_id = self.bot_id
            self._auto_created = True
            print(f"✓ Created bot '{self.bot_name}' with ID: {self.bot_id}")
        except Exception as e:
            raise ConfigurationError(f"Failed to create bot: {e}")

    def _cleanup(self):
        """Clean up auto-created bot on exit."""
        if self._auto_created and self.bot_id:
            try:
                self.client.destroy_bot(self.bot_id)
                print(f"✓ Destroyed bot {self.bot_id}")
            except Exception as e:
                print(f"⚠ Warning: Failed to destroy bot: {e}")

    def destroy(self):
        """Manually destroy the bot (if auto-created)."""
        if self._auto_created and self.bot_id:
            self.client.destroy_bot(self.bot_id)
            self._auto_created = False
            print(f"✓ Destroyed bot {self.bot_id}")
        elif not self._auto_created:
            print("⚠ Warning: Bot was not auto-created, not destroying")

    def on_message(self, func: Callable) -> Callable:
        """
        Decorator to register a message handler.
        Handlers are called for all messages that don't match commands.

        Example:
            @bot.on_message
            def my_handler(message):
                if "hello" in message.text.lower():
                    message.reply("Hi!")
        """
        self._handlers.append(func)
        return func

    def command(self, prefix: str):
        """
        Decorator to register a command handler.
        Commands are checked before regular message handlers.

        Args:
            prefix: Command prefix (e.g., "/prompt", "!help")

        Example:
            @bot.command("/prompt")
            def handle_prompt(message, args):
                # args contains everything after "/prompt"
                message.reply(f"You said: {args}")
        """

        def decorator(func: Callable) -> Callable:
            self._commands[prefix] = func
            return func

        return decorator

    def async_command(self, prefix: str, ack_message: str = None):
        """
        Decorator to register an async command handler.
        Handler will run in a separate thread automatically.

        Args:
            prefix: Command prefix (e.g., "/prompt")
            ack_message: Optional immediate acknowledgment message

        Example:
            @bot.async_command("/prompt", ack_message="Thinking...")
            def handle_prompt(message, args):
                # This runs in a background thread
                time.sleep(5)  # Long operation
                result = my_llm.generate(args)
                message.reply(result)
        """

        def decorator(func: Callable) -> Callable:
            self._async_commands[prefix] = (func, ack_message)
            return func

        return decorator

    def on_unknown_command(self, func: Callable) -> Callable:
        """
        Decorator to register a handler for unknown commands.
        Called when a message starts with a command prefix but doesn't match any registered command.

        Example:
            @bot.on_unknown_command
            def handle_unknown(message, command_text):
                message.reply(f"Unknown command: {command_text}. Try /help")
        """
        self._unknown_command_handler = func
        return func

    def process_message(self, data: dict) -> None:
        """
        Process a GroupMe webhook payload.
        This should be called from your web framework's webhook endpoint.

        Args:
            data: The JSON payload from GroupMe webhook
        """
        # Store message first (if storage enabled)
        if self.storage:
            try:
                self.storage.save_received(data)
            except Exception as e:
                print(f"⚠ Failed to store message: {e}")

        # Parse the message
        message = Message.from_dict(data)

        # Inject reply functionality
        message.reply = lambda text, **kwargs: self.send_message(text, **kwargs)

        # Skip bot's own messages
        if message.sender_type == "bot":
            return

        # Skip messages with no text
        if not message.text:
            # Still call handlers in case they want to process attachments
            for handler in self._handlers:
                try:
                    handler(message)
                except Exception as e:
                    print(f"⚠ Error in handler {handler.__name__}: {e}")
            return

        # Check for async commands first
        for prefix, (handler, ack_message) in self._async_commands.items():
            if message.text.startswith(prefix):
                args = message.text[len(prefix) :].strip()

                # Send acknowledgment if configured
                if ack_message:
                    try:
                        self.send_message(ack_message)
                    except Exception as e:
                        print(f"⚠ Failed to send ack message: {e}")

                # Run handler in thread
                def run_async():
                    try:
                        handler(message, args)
                    except Exception as e:
                        print(f"⚠ Error in async command {prefix}: {e}")

                thread = threading.Thread(target=run_async, daemon=True)
                thread.start()
                return

        # Check for regular commands
        for prefix, handler in self._commands.items():
            if message.text.startswith(prefix):
                args = message.text[len(prefix) :].strip()
                try:
                    handler(message, args)
                except Exception as e:
                    print(f"⚠ Error in command {prefix}: {e}")
                return

        # Check if it looks like a command but wasn't matched
        if message.text.startswith(("/", "!")):
            if self._unknown_command_handler:
                try:
                    self._unknown_command_handler(message, message.text)
                except Exception as e:
                    print(f"⚠ Error in unknown command handler: {e}")
                return

        # Fall through to regular message handlers
        for handler in self._handlers:
            try:
                handler(message)
            except Exception as e:
                print(f"⚠ Error in handler {handler.__name__}: {e}")

    def send_message(self, text: str, image_url: str = None, **kwargs) -> Dict[str, Any]:
        """
        Send a message directly (without processing a webhook).

        Args:
            text: Message text
            image_url: Optional image URL
            **kwargs: Additional arguments passed to client.send_message()

        Returns:
            Response from GroupMe API
        """
        try:
            response = self.client.send_message(text, image_url=image_url, **kwargs)

            # Store sent message (if storage enabled)
            if self.storage and self.group_id:
                try:
                    self.storage.save_sent(text, self.group_id, self.bot_id, image_url)
                except Exception as e:
                    print(f"⚠ Failed to store sent message: {e}")

            return response
        except Exception as e:
            print(f"⚠ Failed to send message: {e}")
            raise

    def send_location(self, name: str, lat: float, lng: float, text: str = "") -> Dict[str, Any]:
        """Send a location attachment."""
        return self.client.send_location(name, lat, lng, text)

    def list_groups(self) -> List[Dict[str, Any]]:
        """List all groups the user belongs to (helpful for finding group_id)."""
        return self.client.list_groups()

    # Storage convenience methods

    def get_db_session(self):
        """
        Get SQLAlchemy session for custom queries.
        Remember to close the session when done!

        Returns:
            SQLAlchemy Session object

        Example:
            from groupme_bot.storage import StoredMessage

            session = bot.get_db_session()
            try:
                messages = session.query(StoredMessage)\\
                    .filter(StoredMessage.text.like('%pizza%'))\\
                    .order_by(StoredMessage.created_at.desc())\\
                    .all()

                # Convert to Message objects
                from groupme_bot import Message
                import json
                msg_objects = [Message.from_dict(json.loads(m.raw_json)) for m in messages]
            finally:
                session.close()
        """
        if not self.storage:
            raise Exception("Storage not enabled. Set enable_storage=True")
        return self.storage.get_session()

    def get_recent_messages(self, limit: int = 50, as_objects: bool = False):
        """
        Get recent messages from storage.

        Args:
            limit: Number of messages to retrieve
            as_objects: If True, return Message objects. If False, return dicts.

        Returns:
            List of Message objects or dicts (newest first)

        Example:
            # Get as dicts
            recent = bot.get_recent_messages(limit=20)

            # Get as Message objects
            messages = bot.get_recent_messages(limit=20, as_objects=True)
            for msg in messages:
                print(f"{msg.name}: {msg.text}")
        """
        if not self.storage:
            raise Exception("Storage not enabled. Set enable_storage=True")

        results = self.storage.get_recent(self.group_id, limit=limit)

        if as_objects:
            return [Message.from_dict(data) for data in results]
        return results

"""GroupMe bot manager with webhook handling and command routing."""

import os
import atexit
import threading
from typing import Callable, List, Optional, Dict, Any
from .client import GroupMeClient
from .models import Message
from .storage import MessageStorage
from .exceptions import ConfigurationError
from .sender import GroupMeBot


class GroupMeBotManager:
    """
    Manager class for handling GroupMe webhooks, command routing, and bot creation.

    The manager creates and manages multiple GroupMeBot instances, handles webhook
    processing, command routing, and provides shared storage across all bots.

    Example:
        manager = GroupMeBotManager(
            api_key="...",
            group_id="...",
            callback_url="https://...",
            enable_storage=True
        )

        # Get the primary webhook bot
        system_bot = manager.primary_bot

        # Create additional bots
        bean_bot = manager.create_bot(name="Bean", bot_id="...")

        # Register commands
        @manager.command("/hello")
        def hello(message, args):
            system_bot.send_message("Hello!")
    """

    def __init__(
        self,
        api_key: str = None,
        group_id: str = None,
        callback_url: Optional[str] = None,
        bot_name: str = "System",
        bot_id: str = None,
        avatar_url: str = None,
        enable_storage: bool = False,
        storage_connection: str = None,
    ):
        """
        Initialize the bot manager and create the primary webhook bot.

        Args:
            api_key: GroupMe API key (or set GROUPME_API_KEY env var)
            group_id: Group ID (or set GROUPME_GROUP_ID env var)
            callback_url: Webhook callback URL (optional, only needed for receiving messages/commands)
            bot_name: Name for the primary bot (default: "System")
            bot_id: Existing bot ID for primary bot (optional, will auto-create if not provided)
            avatar_url: Avatar URL for the primary bot
            enable_storage: If True, enable SQLite message storage for all bots
            storage_connection: Custom DB path (e.g., "sqlite:///myapp.db")

        Raises:
            ConfigurationError: If required credentials are missing
        """
        # Load configuration
        self.api_key = api_key or os.getenv("GROUPME_API_KEY")
        self.group_id = group_id or os.getenv("GROUPME_GROUP_ID")
        self.callback_url = callback_url or os.getenv("GROUPME_CALLBACK_URL")

        if not self.api_key:
            raise ConfigurationError(
                "API key required. Set GROUPME_API_KEY environment variable "
                "or pass api_key to __init__"
            )

        if not self.group_id:
            raise ConfigurationError(
                "Group ID required. Set GROUPME_GROUP_ID environment variable "
                "or pass group_id to __init__"
            )

        # if not self.callback_url:
        #     raise ConfigurationError(
        #         "Callback URL required for webhook handling. Set GROUPME_CALLBACK_URL "
        #         "environment variable or pass callback_url to __init__"
        #     )

        # Initialize shared client (bot_id will be swapped by individual bots)
        self.client = GroupMeClient(self.api_key)

        # Handler storage
        self._handlers: List[Callable] = []
        self._commands: Dict[str, Callable] = {}
        self._async_commands: Dict[str, tuple] = {}  # command -> (handler, ack_message)
        self._unknown_command_handler: Optional[Callable] = None

        # Storage setup
        self.storage: Optional[MessageStorage] = None
        if enable_storage:
            connection_string = storage_connection or "sqlite:///messages.db"
            self.storage = MessageStorage(connection_string)

        # Bot registry
        self._bots: Dict[str, GroupMeBot] = {}
        self._auto_created_bot_ids: List[str] = []

        # Create primary webhook bot immediately
        primary_bot_id = bot_id or os.getenv("GROUPME_BOT_ID")
        if not primary_bot_id:
            # Auto-create the primary bot
            primary_bot_id = self._create_bot_on_groupme(bot_name, avatar_url)
            self._auto_created_bot_ids.append(primary_bot_id)

        # Create the primary bot instance
        self._primary_bot = GroupMeBot(
            bot_id=primary_bot_id,
            name=bot_name,
            client=self.client,
            group_id=self.group_id,
            storage=self.storage,
        )
        self._bots[primary_bot_id] = self._primary_bot

        print(f"✓ Primary bot '{bot_name}' ready with ID: {primary_bot_id}")

        # Register cleanup on exit
        atexit.register(self._cleanup)

    @property
    def primary_bot(self) -> GroupMeBot:
        """Get the primary webhook-handling bot."""
        return self._primary_bot

    def _create_bot_on_groupme(self, name: str, avatar_url: Optional[str] = None) -> str:
        """
        Create a new bot on GroupMe and return its ID.

        Args:
            name: Bot name
            avatar_url: Optional avatar URL

        Returns:
            Bot ID of the created bot

        Raises:
            ConfigurationError: If bot creation fails
        """
        try:
            response = self.client.create_bot(
                name=name,
                group_id=self.group_id,
                callback_url=self.callback_url,
                avatar_url=avatar_url,
            )
            bot_id = response["response"]["bot"]["bot_id"]
            print(f"✓ Created bot '{name}' on GroupMe with ID: {bot_id}")
            return bot_id
        except Exception as e:
            raise ConfigurationError(f"Failed to create bot: {e}")

    def _cleanup(self):
        """Clean up auto-created bots on exit."""
        for bot_id in self._auto_created_bot_ids:
            try:
                self.client.destroy_bot(bot_id)
                print(f"✓ Destroyed auto-created bot {bot_id}")
            except Exception as e:
                print(f"⚠ Warning: Failed to destroy bot {bot_id}: {e}")

    def destroy_bot(self, bot_id: str):
        """
        Manually destroy a bot (only if it was auto-created by this manager).

        Args:
            bot_id: Bot ID to destroy
        """
        if bot_id in self._auto_created_bot_ids:
            self.client.destroy_bot(bot_id)
            self._auto_created_bot_ids.remove(bot_id)
            if bot_id in self._bots:
                del self._bots[bot_id]
            print(f"✓ Destroyed bot {bot_id}")
        else:
            print(f"⚠ Warning: Bot {bot_id} was not auto-created by this manager, not destroying")

    def create_bot(
        self,
        name: str,
        bot_id: Optional[str] = None,
        avatar_url: Optional[str] = None,
        auto_create: bool = True,
    ) -> GroupMeBot:
        """
        Create a new bot instance managed by this manager.

        All bots created by this manager share the same storage (if enabled).

        Args:
            name: Bot name
            bot_id: Existing bot ID (optional, will auto-create if not provided and auto_create=True)
            avatar_url: Avatar URL for auto-created bots
            auto_create: If True and bot_id not provided, create a new bot on GroupMe

        Returns:
            GroupMeBot instance

        Raises:
            ConfigurationError: If bot_id not provided and auto_create=False

        Example:
            # Create a bot with existing bot_id
            bean = manager.create_bot(name="Bean", bot_id="existing_bot_id")

            # Auto-create a new bot
            coffee = manager.create_bot(name="Coffee")  # Will create on GroupMe
        """
        # Check if bot already exists
        if bot_id and bot_id in self._bots:
            print(f"⚠ Bot {bot_id} already exists in manager, returning existing instance")
            return self._bots[bot_id]

        # Get or create bot_id
        if not bot_id:
            if auto_create:
                bot_id = self._create_bot_on_groupme(name, avatar_url)
                self._auto_created_bot_ids.append(bot_id)
            else:
                raise ConfigurationError(
                    f"bot_id required for bot '{name}' (or set auto_create=True)"
                )

        # Create bot instance
        bot = GroupMeBot(
            bot_id=bot_id,
            name=name,
            client=self.client,
            group_id=self.group_id,
            storage=self.storage,
        )

        self._bots[bot_id] = bot
        print(f"✓ Bot '{name}' ready with ID: {bot_id}")
        return bot

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

    def process_webhook(self, data: dict) -> None:
        """
        Process a GroupMe webhook payload.
        This should be called from your web framework's webhook endpoint.

        Args:
            data: The JSON payload from GroupMe webhook

        Example:
            @app.route("/webhook", methods=["POST"])
            def webhook():
                manager.process_webhook(request.get_json())
                return "ok", 200
        """
        # Store message first (if storage enabled)
        if self.storage:
            try:
                self.storage.save_received(data)
            except Exception as e:
                print(f"⚠ Failed to store message: {e}")

        # Parse the message
        message = Message.from_dict(data)

        # Inject reply functionality using primary bot
        message.reply = lambda text, **kwargs: self.primary_bot.send_message(text, **kwargs)

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
                        self.primary_bot.send_message(ack_message)
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

    # Keep process_message as an alias for backward compatibility during transition
    def process_message(self, data: dict) -> None:
        """Alias for process_webhook (deprecated, use process_webhook instead)."""
        return self.process_webhook(data)

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
            from group_py.storage import StoredMessage

            session = bot.get_db_session()
            try:
                messages = session.query(StoredMessage)\\
                    .filter(StoredMessage.text.like('%pizza%'))\\
                    .order_by(StoredMessage.created_at.desc())\\
                    .all()

                # Convert to Message objects
                from group_py import Message
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

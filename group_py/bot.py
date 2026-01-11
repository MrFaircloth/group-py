"""GroupMe bot manager with webhook handling and command routing."""

import os
import atexit
import threading
from typing import Callable, List, Optional, Dict, Any
from .client import GroupMeClient
from .models import Message
from .exceptions import ConfigurationError
from .sender import GroupMeBot


class GroupMeBotManager:
    """
    Manager class for handling GroupMe webhooks, command routing, and bot creation.

    The manager creates and manages multiple GroupMeBot instances, handles webhook
    processing, and command routing.

    Example:
        manager = GroupMeBotManager(
            api_key="...",
            group_id="...",
            callback_url="https://..."
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
        config_file: str = None,
        enable_realtime: bool = False,
        user_id: str = None,
    ):
        """
        Initialize the bot manager and create the primary webhook bot.

        Args:
            api_key: GroupMe API key (or set GROUPME_API_KEY env var)
            group_id: Group ID (or set GROUPME_GROUP_ID env var)
            callback_url: Webhook callback URL (optional, only needed for webhook mode)
            bot_name: Name for the primary bot (default: "System")
            bot_id: Existing bot ID for primary bot (optional, will auto-create if not provided)
            avatar_url: Avatar URL for the primary bot
            config_file: Path to YAML config file (optional, defaults to groupme_config.yaml if exists)
            enable_realtime: Enable real-time WebSocket connection (default: False)
            user_id: GroupMe user ID (required if enable_realtime=True)

        Raises:
            ConfigurationError: If required credentials are missing

        Example:
            # Auto-load from groupme_config.yaml if it exists
            manager = GroupMeBotManager()

            # Load from specific config file
            manager = GroupMeBotManager(config_file="my_config.yaml")

            # Or use traditional parameters
            manager = GroupMeBotManager(api_key="...", group_id="...")

            # Enable real-time WebSocket mode
            manager = GroupMeBotManager(
                api_key="...",
                group_id="...",
                user_id="...",
                enable_realtime=True
            )
        """
        # Check if we should load from YAML config
        should_load_yaml = False
        yaml_path = None

        # If config_file explicitly provided, use it
        if config_file:
            yaml_path = config_file
            should_load_yaml = True
        # If no arguments provided, check for default config file
        elif not any([api_key, group_id, callback_url, bot_id, avatar_url, bot_name != "System", user_id, enable_realtime]):
            # Check environment variable first
            default_path = os.getenv("GROUPME_CONFIG_FILE", "groupme_config.yaml")
            if os.path.exists(default_path):
                yaml_path = default_path
                should_load_yaml = True

        # Load from YAML if we should
        if should_load_yaml:
            from .config import load_yaml_config, get_config_value
            config = load_yaml_config(yaml_path)

            # Get realtime config
            realtime_config = config.get("realtime", {})

            # Extract values from config (params override config)
            api_key = api_key or get_config_value(config, "api_key")
            group_id = group_id or get_config_value(config, "group_id")
            callback_url = callback_url or get_config_value(config, "callback_url")
            bot_name = bot_name if bot_name != "System" else get_config_value(config, "bot_name", "System")
            bot_id = bot_id or get_config_value(config, "bot_id")
            avatar_url = avatar_url or get_config_value(config, "avatar_url")
            user_id = user_id or get_config_value(config, "user_id")
            if not enable_realtime:
                enable_realtime = realtime_config.get("enabled", False)

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

        # Handler registration
        self._handlers: List[Callable] = []
        self._commands: Dict[str, Callable] = {}
        self._async_commands: Dict[str, tuple] = {}  # command -> (handler, ack_message)
        self._unknown_command_handler: Optional[Callable] = None
        self._preprocessors: List[Callable] = []  # Global handlers that run for ALL messages

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
        )
        self._bots[primary_bot_id] = self._primary_bot

        print(f"✓ Primary bot '{bot_name}' ready with ID: {primary_bot_id}")

        # Realtime setup
        self.realtime_manager: Optional[Any] = None
        self.user_id = user_id or os.getenv("GROUPME_USER_ID")

        if enable_realtime:
            if not self.user_id:
                raise ConfigurationError(
                    "user_id required for realtime mode. Set GROUPME_USER_ID "
                    "environment variable or pass user_id to __init__"
                )

            from .realtime import RealtimeManager

            self.realtime_manager = RealtimeManager(
                user_id=self.user_id,
                group_id=self.group_id,
                message_callback=self._handle_realtime_message
            )
            self.realtime_manager.start()
            print(f"✓ Real-time WebSocket client started for user {self.user_id}")

        # Register cleanup on exit
        atexit.register(self._cleanup)

    @classmethod
    def from_yaml(cls, config_path: str) -> 'GroupMeBotManager':
        """
        Create bot manager from YAML configuration file.

        Args:
            config_path: Path to YAML config file

        Returns:
            Initialized GroupMeBotManager

        Raises:
            ConfigError: If config file is invalid or missing required fields

        Example:
            manager = GroupMeBotManager.from_yaml("bots.yaml")

        Config format:
            api_key: "your_api_key"
            group_id: "your_group_id"
            callback_url: "https://example.com/webhook"  # optional (not needed for realtime)
            bot_name: "System"  # optional, defaults to "System"
            bot_id: "existing_bot_id"  # optional
            avatar_url: "https://..."  # optional
            user_id: "your_user_id"  # optional (required for realtime mode)

            # Optional: Real-time WebSocket configuration
            realtime:
              enabled: true  # Enable WebSocket mode (default: false)
              # Additional realtime options can be added here in future
        """
        from .config import load_yaml_config, get_config_value

        config = load_yaml_config(config_path)

        # Get realtime config
        realtime_config = config.get("realtime", {})
        enable_realtime = realtime_config.get("enabled", False)

        # Extract manager config
        return cls(
            api_key=get_config_value(config, "api_key"),
            group_id=get_config_value(config, "group_id"),
            callback_url=get_config_value(config, "callback_url"),
            bot_name=get_config_value(config, "bot_name", "System"),
            bot_id=get_config_value(config, "bot_id"),
            avatar_url=get_config_value(config, "avatar_url"),
            user_id=get_config_value(config, "user_id"),
            enable_realtime=enable_realtime,
        )

    @property
    def primary_bot(self) -> GroupMeBot:
        """Get the primary webhook-handling bot."""
        return self._primary_bot

    def _create_bot_on_groupme(self, name: str, avatar_url: Optional[str] = None) -> str:
        """
        Create a new bot on GroupMe and return its ID.

        Before creating, checks if a bot with the same name already exists
        in the group. If found, reuses the existing bot to prevent orphans
        from accumulating after crashes or restarts.

        Args:
            name: Bot name
            avatar_url: Optional avatar URL

        Returns:
            Bot ID of the created or recovered bot

        Raises:
            ConfigurationError: If bot creation fails
        """
        # Check for existing bot with same name in group (crash recovery)
        existing_bot = self.client.find_bot(name, self.group_id)
        if existing_bot:
            bot_id = existing_bot["bot_id"]
            print(f"✓ Recovered existing bot '{name}' with ID: {bot_id}")
            return bot_id

        # No existing bot found, create new one
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
            callback: Optional function to call for each message (e.g., for storage)
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
            if messages and messages[-1].created_at < cutoff_time:
                break

            # Stop if we got fewer messages than requested (no more to fetch)
            if len(messages) < batch_size:
                break

            before_id = messages[-1].id
            if total_fetched > 0 and total_fetched % 100 == 0:
                print(f"  Fetched {total_fetched} messages...")

        print(f"✓ Backfill complete: {total_fetched} messages")
        return total_fetched

    def _cleanup(self):
        """Clean up auto-created bots and realtime connection on exit."""
        # Stop realtime client first
        if self.realtime_manager:
            try:
                self.realtime_manager.stop()
                print("✓ Stopped real-time WebSocket client")
            except Exception as e:
                print(f"⚠ Warning: Failed to stop realtime client: {e}")

        # Destroy auto-created bots
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

    def on_any_message(self, func: Callable) -> Callable:
        """
        Decorator to register a global message handler.

        This handler runs for ALL messages BEFORE command routing.
        Perfect for: logging, storage, sanitization, analytics.

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
        # Parse the message
        message = Message.from_dict(data)

        # Inject reply functionality using primary bot
        message.reply = lambda text, **kwargs: self.primary_bot.send_message(text, **kwargs)

        # Skip bot's own messages
        if message.sender_type == "bot":
            return

        # Run preprocessors FIRST (before any routing)
        for preprocessor in self._preprocessors:
            try:
                preprocessor(message)
            except Exception as e:
                print(f"⚠ Error in preprocessor {preprocessor.__name__}: {e}")

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


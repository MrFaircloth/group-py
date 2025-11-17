# GroupMe Bot Package Rework Plan - FINAL

## Overview
Rebuild the GroupMe bot package from scratch with a focus on simplicity and streamlined integration into any application. The package provides easy bot management, message routing with commands, automatic message storage, and support for multiple bots (send-only and full webhook handlers).

## Core Requirements
- Python 3.8+ support
- Minimal required configuration (API key via environment variables)
- Auto-create and auto-cleanup bots when bot_id not provided
- Command routing system for easy message handling
- Async command support (automatic threading for long-running operations)
- Optional SQLite message storage
- Support for rich media (images, locations)
- Support for multiple bots (one handles webhooks, others just send)
- Type hints throughout
- Modern packaging with pyproject.toml
- NO web framework dependencies (users integrate into their own Flask/Django/etc apps)

## Project Structure

```
groupme_bot/
├── groupme_bot/
│   ├── __init__.py          # Package exports
│   ├── bot.py               # Main GroupMeBot class
│   ├── sender.py            # GroupMeSender class (send-only)
│   ├── client.py            # GroupMe API client
│   ├── models.py            # Message dataclasses
│   ├── storage.py           # SQLite storage handler
│   └── exceptions.py        # Custom exceptions
├── examples/
│   ├── flask_bot.py         # Flask integration example
│   ├── django_bot.py        # Django integration example
│   ├── multi_bot.py         # Multiple bots example
│   └── .env.example         # Example environment variables
├── tests/
│   └── test_bot.py
├── pyproject.toml
├── README.md
└── .gitignore
```

## Implementation Steps

### 1. Setup Package Structure (pyproject.toml)
```toml
[project]
name = "groupme-bot"
version = "2.0.0"
description = "Simplified GroupMe bot framework with command routing and storage"
requires-python = ">=3.12"
dependencies = [
    "requests>=2.31.0",
    "python-dotenv>=1.0.0",
    "sqlalchemy>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0",
    "flask>=3.0.0",  # For examples only
]
```

### 2. Create Models (models.py)
Define dataclasses for GroupMe messages with type hints:

```python
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import json

@dataclass
class Message:
    id: str
    text: Optional[str]
    user_id: str
    name: str
    group_id: str
    created_at: int
    system: bool
    sender_type: str
    avatar_url: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        """
        Parse the GroupMe webhook payload into a Message object.
        Handle missing/optional fields gracefully.
        """
        return cls(
            id=data.get('id', ''),
            text=data.get('text'),
            user_id=data.get('user_id', ''),
            name=data.get('name', 'Unknown'),
            group_id=data.get('group_id', ''),
            created_at=data.get('created_at', 0),
            system=data.get('system', False),
            sender_type=data.get('sender_type', 'user'),
            avatar_url=data.get('avatar_url'),
            attachments=data.get('attachments', [])
        )
    
    @classmethod
    def from_cursor(cls, cursor) -> List['Message']:
        """
        Convert database cursor/query results to Message objects.
        Works with both SQLAlchemy results and raw SQL cursors.
        
        Args:
            cursor: SQLAlchemy query result or raw cursor with raw_json column
        
        Returns:
            List of Message objects
        
        Example with SQLAlchemy:
            from groupme_bot.storage import StoredMessage
            session = bot.get_db_session()
            results = session.query(StoredMessage).filter(...).all()
            messages = Message.from_query_results(results)
            session.close()
        
        Example with raw SQL:
            from sqlalchemy import text
            session = bot.get_db_session()
            result = session.execute(text("SELECT raw_json FROM groupme_messages WHERE ..."))
            messages = Message.from_cursor(result)
            session.close()
        """
        results = []
        for row in cursor:
            # Handle SQLAlchemy model objects
            if hasattr(row, 'raw_json'):
                data = json.loads(row.raw_json)
            # Handle raw SQL results (tuple/list)
            else:
                data = json.loads(row[0])
            results.append(cls.from_dict(data))
        return results
    
    @classmethod
    def from_query_results(cls, results) -> List['Message']:
        """
        Convert SQLAlchemy query results (list of StoredMessage objects) to Message objects.
        
        Args:
            results: List of StoredMessage objects from SQLAlchemy query
        
        Returns:
            List of Message objects
        
        Example:
            from groupme_bot.storage import StoredMessage
            session = bot.get_db_session()
            results = session.query(StoredMessage)\
                .filter(StoredMessage.text.like('%pizza%'))\
                .all()
            messages = Message.from_query_results(results)
            session.close()
        """
        return [cls.from_dict(json.loads(r.raw_json)) for r in results]
    
    def has_image(self) -> bool:
        """Check if message contains an image attachment"""
        if not self.attachments:
            return False
        return any(a.get('type') == 'image' for a in self.attachments)
    
    def get_image_url(self) -> Optional[str]:
        """Get the first image URL from attachments"""
        if not self.attachments:
            return None
        for a in self.attachments:
            if a.get('type') == 'image':
                return a.get('url')
        return None
    
    def has_location(self) -> bool:
        """Check if message contains a location attachment"""
        if not self.attachments:
            return False
        return any(a.get('type') == 'location' for a in self.attachments)
    
    def get_location(self) -> Optional[tuple]:
        """Get location as (lat, lng, name) tuple"""
        if not self.attachments:
            return None
        for a in self.attachments:
            if a.get('type') == 'location':
                return (a.get('lat'), a.get('lng'), a.get('name'))
        return None
    
    def reply(self, text: str, **kwargs):
        """
        Reply to this message. This method is injected by the Bot class.
        Will be available after message is processed by bot.
        """
        raise NotImplementedError("Reply method not initialized")
```

Key points:
- Use dataclass for clean structure
- `from_dict` classmethod to parse GroupMe webhook JSON
- `from_cursor` classmethod to convert DB queries to Message objects
- Keep only essential fields
- `sender_type` is important to filter out bot's own messages
- Helper methods for checking attachments (images, locations)
- `reply()` will be injected by the Bot class

### 3. Build API Client (client.py)
Create a `GroupMeClient` class:

```python
import requests
from typing import Dict, Any, Optional, List
from .exceptions import APIError

class GroupMeClient:
    BASE_URL = "https://api.groupme.com/v3"
    
    def __init__(self, api_key: str, bot_id: Optional[str] = None):
        self.api_key = api_key
        self.bot_id = bot_id
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def create_bot(self, name: str, group_id: str, callback_url: str, 
                   avatar_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new bot in a group.
        
        Returns:
            Response dict containing bot info including bot_id
        """
        url = f"{self.BASE_URL}/bots"
        payload = {
            "bot": {
                "name": name,
                "group_id": group_id,
                "callback_url": callback_url,
            }
        }
        if avatar_url:
            payload["bot"]["avatar_url"] = avatar_url
        
        params = {"token": self.api_key}
        
        try:
            response = self.session.post(url, json=payload, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise APIError(f"Failed to create bot: {e}")
    
    def destroy_bot(self, bot_id: str) -> None:
        """Delete a bot"""
        url = f"{self.BASE_URL}/bots/destroy"
        payload = {"bot_id": bot_id}
        params = {"token": self.api_key}
        
        try:
            response = self.session.post(url, json=payload, params=params, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise APIError(f"Failed to destroy bot: {e}")
    
    def send_message(self, text: str, image_url: Optional[str] = None,
                    attachments: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Send a message as the bot.
        
        Args:
            text: Message text
            image_url: Optional image URL to attach
            attachments: Optional list of attachment dicts for advanced use
        
        Returns:
            Response dict from GroupMe API
        """
        if not self.bot_id:
            raise APIError("Cannot send message: bot_id not set")
        
        url = f"{self.BASE_URL}/bots/post"
        payload = {
            "bot_id": self.bot_id,
            "text": text
        }
        
        # Handle image_url shorthand
        if image_url:
            payload["picture_url"] = image_url
        
        # Handle custom attachments
        if attachments:
            payload["attachments"] = attachments
        
        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise APIError(f"Failed to send message: {e}")
    
    def send_location(self, name: str, lat: float, lng: float, text: str = "") -> Dict[str, Any]:
        """
        Send a location attachment.
        
        Args:
            name: Location name/label
            lat: Latitude
            lng: Longitude
            text: Optional message text
        """
        attachments = [{
            "type": "location",
            "lat": str(lat),
            "lng": str(lng),
            "name": name
        }]
        return self.send_message(text or name, attachments=attachments)
    
    def get_bot_info(self) -> Dict[str, Any]:
        """Fetch information about the bot"""
        url = f"{self.BASE_URL}/bots"
        params = {"token": self.api_key}
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise APIError(f"Failed to get bot info: {e}")
    
    def list_groups(self) -> List[Dict[str, Any]]:
        """List all groups the user belongs to"""
        url = f"{self.BASE_URL}/groups"
        params = {"token": self.api_key}
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json().get('response', [])
        except requests.exceptions.RequestException as e:
            raise APIError(f"Failed to list groups: {e}")
```

Key points:
- Use requests library for HTTP calls
- Raise custom exceptions on API errors
- Support creating and destroying bots dynamically
- Support images via `image_url` parameter
- Support locations via `send_location()` method
- Support generic attachments for future expansion
- Include timeout on all requests
- Provide `list_groups()` helper to find group_id

### 4. Build Storage Handler (storage.py)
Create a `MessageStorage` class using SQLAlchemy:

```python
from sqlalchemy import create_engine, Column, String, Integer, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Dict, Any, Optional
import json

Base = declarative_base()

class StoredMessage(Base):
    """SQLAlchemy model for stored messages"""
    __tablename__ = 'groupme_messages'
    
    id = Column(String(255), primary_key=True)
    group_id = Column(String(255), index=True, nullable=False)
    user_id = Column(String(255), index=True, nullable=False)
    text = Column(Text, nullable=True)
    created_at = Column(Integer, index=True, nullable=False)
    direction = Column(String(20), index=True, nullable=False)  # 'received' or 'sent'
    raw_json = Column(Text, nullable=False)
    
    __table_args__ = (
        Index('idx_group_user', 'group_id', 'user_id'),
        Index('idx_created_at_desc', created_at.desc()),
    )

class MessageStorage:
    """
    Handles storage of GroupMe messages using SQLAlchemy.
    Supports SQLite, PostgreSQL, MySQL, and other SQLAlchemy-compatible databases.
    """
    
    def __init__(self, connection_string: str = "sqlite:///messages.db"):
        """
        Initialize storage with database connection.
        
        Args:
            connection_string: SQLAlchemy connection string
                Examples:
                - "sqlite:///messages.db" (default)
                - "postgresql://user:pass@localhost/dbname"
                - "mysql://user:pass@localhost/dbname"
        """
        self.connection_string = connection_string
        self.engine = create_engine(connection_string)
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        
        # Create session factory
        self.Session = sessionmaker(bind=self.engine)
    
    def get_session(self) -> Session:
        """
        Get a new SQLAlchemy session for custom queries.
        Remember to close the session when done!
        
        Returns:
            SQLAlchemy Session object
        
        Example:
            session = storage.get_session()
            try:
                results = session.query(StoredMessage).filter(...).all()
            finally:
                session.close()
        """
        return self.Session()
    
    def save_received(self, message_data: dict):
        """
        Store incoming webhook payload.
        
        Args:
            message_data: Raw message dict from GroupMe webhook
        """
        session = self.Session()
        try:
            msg = StoredMessage(
                id=message_data['id'],
                group_id=message_data.get('group_id', ''),
                user_id=message_data.get('user_id', ''),
                text=message_data.get('text', ''),
                created_at=message_data.get('created_at', 0),
                direction='received',
                raw_json=json.dumps(message_data)
            )
            session.merge(msg)  # INSERT or UPDATE if exists
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def save_sent(self, text: str, group_id: str, bot_id: str, image_url: Optional[str] = None):
        """
        Store outgoing message.
        
        Args:
            text: Message text
            group_id: Group ID
            bot_id: Bot ID that sent the message
            image_url: Optional image URL
        """
        import time
        session = self.Session()
        try:
            # Create synthetic message object
            message_data = {
                "id": f"sent_{int(time.time() * 1000)}_{bot_id}",
                "group_id": group_id,
                "user_id": bot_id,
                "text": text,
                "created_at": int(time.time()),
                "sender_type": "bot",
                "direction": "sent"
            }
            
            if image_url:
                message_data["picture_url"] = image_url
            
            msg = StoredMessage(
                id=message_data['id'],
                group_id=group_id,
                user_id=bot_id,
                text=text,
                created_at=message_data['created_at'],
                direction='sent',
                raw_json=json.dumps(message_data)
            )
            session.add(msg)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_recent(self, group_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent messages as dicts.
        
        Args:
            group_id: Group ID to filter by
            limit: Number of messages to retrieve
        
        Returns:
            List of message dicts (newest first)
        """
        session = self.Session()
        try:
            results = session.query(StoredMessage)\
                .filter(StoredMessage.group_id == group_id)\
                .order_by(StoredMessage.created_at.desc())\
                .limit(limit)\
                .all()
            
            return [json.loads(msg.raw_json) for msg in results]
        finally:
            session.close()
```

Key points:
- Uses SQLAlchemy ORM for database abstraction
- Supports SQLite, PostgreSQL, MySQL, and any SQLAlchemy-compatible database
- `StoredMessage` model maps to `groupme_messages` table
- Automatic table creation with proper indexes
- `get_session()` method for custom queries
- Proper transaction handling with rollback on errors
- Connection pooling handled by SQLAlchemy
- Thread-safe session management

### 5. Build Main Bot Class (bot.py)
Create the `GroupMeBot` class that ties everything together:

```python
import os
import atexit
import sqlite3
import threading
from typing import Callable, List, Optional, Dict, Any
from .client import GroupMeClient
from .models import Message
from .storage import MessageStorage
from .exceptions import ConfigurationError

class GroupMeBot:
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
        storage_connection: str = None
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
        """Create a new bot and store its ID"""
        try:
            response = self.client.create_bot(
                name=self.bot_name,
                group_id=self.group_id,
                callback_url=self.callback_url,
                avatar_url=self.avatar_url
            )
            self.bot_id = response["response"]["bot"]["bot_id"]
            self.client.bot_id = self.bot_id
            self._auto_created = True
            print(f"✓ Created bot '{self.bot_name}' with ID: {self.bot_id}")
        except Exception as e:
            raise ConfigurationError(f"Failed to create bot: {e}")
    
    def _cleanup(self):
        """Clean up auto-created bot on exit"""
        if self._auto_created and self.bot_id:
            try:
                self.client.destroy_bot(self.bot_id)
                print(f"✓ Destroyed bot {self.bot_id}")
            except Exception as e:
                print(f"⚠ Warning: Failed to destroy bot: {e}")
    
    def destroy(self):
        """Manually destroy the bot (if auto-created)"""
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
                args = message.text[len(prefix):].strip()
                
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
                args = message.text[len(prefix):].strip()
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
        """Send a location attachment"""
        return self.client.send_location(name, lat, lng, text)
    
    def list_groups(self) -> List[Dict[str, Any]]:
        """List all groups the user belongs to (helpful for finding group_id)"""
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
                messages = session.query(StoredMessage)\
                    .filter(StoredMessage.text.like('%pizza%'))\
                    .order_by(StoredMessage.created_at.desc())\
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
```

Key points:
- Load credentials from environment by default
- Raise clear errors if credentials missing
- Use decorator pattern for registering handlers
- Auto-create bot if bot_id not provided and auto_create=True
- Register atexit handler to destroy auto-created bots
- Command routing system checks commands before regular handlers
- Async command support with automatic threading
- Unknown command handler for unrecognized commands
- Optional SQLite storage with convenience methods
- `process_message()` is the main entry point for webhook data
- Skip bot's own messages automatically
- Inject `reply()` method into Message objects
- Handle exceptions in handlers gracefully (don't crash on one bad handler)

### 6. Build Send-Only Bot Class (sender.py)
Create a lightweight `GroupMeSender` class for bots that only send:

```python
import os
from typing import Dict, Any, Optional
from .client import GroupMeClient
from .exceptions import ConfigurationError

class GroupMeSender:
    """
    Lightweight client for sending messages only.
    Use this for secondary bots that don't need to process webhooks.
    
    Example:
        bean = GroupMeSender(bot_id="...", api_key="...")
        bean.send_message("Hello from Bean!")
    """
    
    def __init__(self, bot_id: str = None, api_key: str = None):
        """
        Initialize a send-only bot.
        
        Args:
            bot_id: Bot ID (or set GROUPME_BOT_ID env var)
            api_key: API key (or set GROUPME_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("GROUPME_API_KEY")
        self.bot_id = bot_id or os.getenv("GROUPME_BOT_ID")
        
        if not self.api_key or not self.bot_id:
            raise ConfigurationError(
                "API key and bot ID required. Set GROUPME_API_KEY and "
                "GROUPME_BOT_ID environment variables or pass to __init__"
            )
        
        self.client = GroupMeClient(self.api_key, self.bot_id)
    
    def send_message(self, text: str, image_url: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Send a message"""
        return self.client.send_message(text, image_url=image_url, **kwargs)
    
    def send_location(self, name: str, lat: float, lng: float, text: str = "") -> Dict[str, Any]:
        """Send a location attachment"""
        return self.client.send_location(name, lat, lng, text)
```

Key points:
- Minimal interface - just for sending
- No webhook processing, no handlers, no storage
- Perfect for secondary bots in multi-bot setups

### 7. Create Custom Exceptions (exceptions.py)
Define exceptions:

```python
class GroupMeBotError(Exception):
    """Base exception for all bot errors"""
    pass

class ConfigurationError(GroupMeBotError):
    """Raised when bot is misconfigured (missing credentials, etc.)"""
    pass

class APIError(GroupMeBotError):
    """Raised when GroupMe API returns an error"""
    pass
```

### 8. Package Exports (__init__.py)
Export the main classes:

```python
from .bot import GroupMeBot
from .sender import GroupMeSender
from .models import Message
from .exceptions import GroupMeBotError, ConfigurationError, APIError

__version__ = "2.0.0"
__all__ = [
    "GroupMeBot",
    "GroupMeSender",
    "Message",
    "GroupMeBotError",
    "ConfigurationError",
    "APIError"
]
```

### 9. Create Flask Example (examples/flask_bot.py)
```python
from flask import Flask, request
from groupme_bot import GroupMeBot

# Initialize bot with storage enabled
bot = GroupMeBot(
    group_id="your_group_id",
    callback_url="https://yourserver.com/groupme-webhook",
    bot_name="Flask Bot",
    enable_storage=True,
    auto_create=True  # Will create and destroy automatically
)

# Command: /prompt - sends to LLM
@bot.async_command("/prompt", ack_message="🤔 Thinking...")
def handle_prompt(message, args):
    """Handle LLM prompts with context"""
    import time
    
    # Get conversation context
    context = bot.get_recent_messages(limit=20, as_objects=True)
    context_text = "\n".join([f"{m.name}: {m.text}" for m in reversed(context) if m.text])
    
    # Simulate LLM call
    time.sleep(2)
    response = f"Response to: {args}\n\nContext used: {len(context)} messages"
    
    message.reply(response)

# Command: /search - search message history
@bot.command("/search")
def handle_search(message, args):
    """Search message history"""
    from groupme_bot.storage import StoredMessage
    
    session = bot.get_db_session()
    try:
        results = session.query(StoredMessage)\
            .filter(StoredMessage.text.like(f'%{args}%'))\
            .order_by(StoredMessage.created_at.desc())\
            .limit(10)\
            .all()
        
        from groupme_bot import Message
        messages = Message.from_query_results(results)
        
        if messages:
            summary = f"Found {len(messages)} messages:\n"
            for msg in messages[:3]:
                summary += f"• {msg.name}: {msg.text[:50]}...\n"
            message.reply(summary)
        else:
            message.reply(f"No messages found matching '{args}'")
    finally:
        session.close()

# Unknown command handler
@bot.on_unknown_command
def handle_unknown(message, command_text):
    message.reply(f"❓ Unknown command. Try:\n/prompt <text>\n/search <query>")

# Catch-all for regular messages
@bot.on_message
def handle_message(message):
    if message.text and "hello" in message.text.lower():
        message.reply("👋 Hi there!")

# Create Flask app
app = Flask(__name__)

@app.route('/groupme-webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    bot.process_message(data)
    return "ok", 200

@app.route('/health')
def health():
    return {"status": "ok", "bot_id": bot.bot_id}

if __name__ == "__main__":
    print(f"🤖 Bot running with ID: {bot.bot_id}")
    app.run(port=3000, debug=True)
```

### 10. Create Django Example (examples/django_bot.py)
```python
# bot_instance.py - Create bot instance once
from groupme_bot import GroupMeBot
from django.conf import settings

# Build SQLAlchemy connection string from Django database settings
db = settings.DATABASES['default']
engine = db['ENGINE']

if 'postgresql' in engine:
    connection_string = f"postgresql://{db['USER']}:{db['PASSWORD']}@{db['HOST']}:{db['PORT']}/{db['NAME']}"
elif 'mysql' in engine:
    connection_string = f"mysql://{db['USER']}:{db['PASSWORD']}@{db['HOST']}:{db['PORT']}/{db['NAME']}"
else:
    # Fallback to SQLite
    connection_string = f"sqlite:///{db['NAME']}"

bot = GroupMeBot(
    enable_storage=True,
    storage_connection=connection_string  # Use Django's database!
)

@bot.command("/echo")
def handle_echo(message, args):
    message.reply(f"You said: {args}")

@bot.on_message
def handle_message(message):
    if message.text and "hello" in message.text.lower():
        message.reply("Hi from Django!")

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
        data = json.loads(request.body)
        bot.process_message(data)
        return JsonResponse({"ok": True})

# urls.py
from django.urls import path
from .views import GroupMeWebhook

urlpatterns = [
    path('groupme-webhook/', GroupMeWebhook.as_view()),
]
```

### 11. Create Multi-Bot Example (examples/multi_bot.py)
```python
from flask import Flask, request
from groupme_bot import GroupMeBot, GroupMeSender

# Main bot - handles webhooks
system_bot = GroupMeBot(
    group_id="your_group_id",
    callback_url="https://yourserver.com/webhook",
    bot_name="System",
    enable_storage=True
)

# Secondary bot - only sends messages
bean_bot = GroupMeSender(
    bot_id="bean_bot_id",
    api_key="your_api_key"
)

# System bot handles commands
@system_bot.command("/bean")
def bean_command(message, args):
    """Make Bean say something"""
    bean_bot.send_message(f"🫘 Bean says: {args}")

@system_bot.command("/status")
def status_command(message, args):
    """Check bot status"""
    recent = system_bot.get_recent_messages(limit=10)
    message.reply(f"📊 Last {len(recent)} messages stored")

# Regular message handling
@system_bot.on_message
def handle_regular(message):
    if message.has_image():
        bean_bot.send_message("🖼️ Nice image!")

# Flask setup
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    system_bot.process_message(request.get_json())
    return "ok", 200

if __name__ == "__main__":
    app.run(port=3000)
```

### 12. Environment Variables (.env.example)
```
# Required
GROUPME_API_KEY=your_api_key_here

# Option 1: Use existing bot
GROUPME_BOT_ID=your_bot_id_here

# Option 2: Auto-create bot (requires these instead of BOT_ID)
GROUPME_GROUP_ID=your_group_id_here
GROUPME_CALLBACK_URL=https://yourserver.com/groupme-webhook
```

### 13. Documentation (README.md)
Include sections:

**Installation**
```bash
pip install groupme-bot
```

**Quick Start**
```python
from groupme_bot import GroupMeBot

bot = GroupMeBot(
    group_id="...",
    callback_url="https://yourserver.com/webhook",
    enable_storage=True
)

@bot.command("/hello")
def hello(message, args):
    message.reply("Hi there!")

# In your Flask/Django view:
bot.process_message(request.get_json())
```

**Getting Started**
- How to get API key from GroupMe Developer Portal
- How to find your group_id (use `bot.list_groups()`)
- Setting up ngrok or similar for local development
- Configuring callback URL in GroupMe

**Features**
- Auto-create and cleanup bots
- Command routing (`@bot.command()`)
- Async commands for long-running operations (`@bot.async_command()`)
- Message storage with SQLite
- Multiple bots support (webhook handler + send-only)
- Rich media (images, locations)
- Custom query support via direct DB access

**API Reference**

*GroupMeBot*
- `__init__(...)` - Configuration options
- `@on_message` - Register message handler
- `@command(prefix)` - Register command
- `@async_command(prefix, ack_message)` - Register async command
- `@on_unknown_command` - Handle unknown commands
- `process_message(data)` - Process webhook payload
- `send_message(text, image_url)` - Send message
- `send_location(name, lat, lng)` - Send location
- `get_db_session()` - Get SQLAlchemy session for custom queries
- `get_recent_messages(limit, as_objects)` - Retrieve stored messages
- `list_groups()` - List available groups (helpful for finding group_id)

*GroupMeSender*
- `__init__(bot_id, api_key)` - Initialize send-only bot
- `send_message(text, image_url)` - Send message
- `send_location(name, lat, lng)` - Send location

*Message*
- `from_dict(data)` - Parse webhook payload
- `from_cursor(cursor)` - Convert DB query to Messages
- `has_image()` - Check for image attachment
- `get_image_url()` - Get image URL
- `has_location()` - Check for location
- `get_location()` - Get (lat, lng, name)
- `reply(text, **kwargs)` - Reply to message

**Storage & Queries**

Using built-in storage with SQLAlchemy:
```python
bot = GroupMeBot(
    enable_storage=True,
    storage_connection="postgresql://localhost/myapp"  # Any SQLAlchemy DB
)

# Get recent messages
messages = bot.get_recent_messages(limit=50, as_objects=True)

# Custom queries with SQLAlchemy ORM
from groupme_bot.storage import StoredMessage

session = bot.get_db_session()
try:
    results = session.query(StoredMessage)\
        .filter(StoredMessage.text.like('%pizza%'))\
        .order_by(StoredMessage.created_at.desc())\
        .limit(10)\
        .all()
    
    # Convert to Message objects
    from groupme_bot import Message
    messages = Message.from_query_results(results)
finally:
    session.close()

# Or use raw SQL
from sqlalchemy import text
session = bot.get_db_session()
try:
    result = session.execute(text("""
        SELECT raw_json FROM groupme_messages
        WHERE text LIKE :query
        ORDER BY created_at DESC
    """), {"query": "%pizza%"})
    
    messages = Message.from_cursor(result)
finally:
    session.close()
```

**Database Support**
```python
# SQLite (default)
bot = GroupMeBot(enable_storage=True)

# PostgreSQL
bot = GroupMeBot(
    enable_storage=True,
    storage_connection="postgresql://user:pass@localhost/dbname"
)

# MySQL
bot = GroupMeBot(
    enable_storage=True,
    storage_connection="mysql://user:pass@localhost/dbname"
)

# Use Django's database
from django.conf import settings
db = settings.DATABASES['default']
connection = f"postgresql://{db['USER']}:{db['PASSWORD']}@{db['HOST']}/{db['NAME']}"
bot = GroupMeBot(enable_storage=True, storage_connection=connection)
```

**Integration Examples**
- Flask integration
- Django integration
- FastAPI integration (brief example)
- Multiple bots setup

**Testing**
```python
# Create test message
test_data = {
    "id": "test123",
    "text": "/hello world",
    "user_id": "user123",
    "name": "Test User",
    "group_id": "group123",
    "created_at": 1234567890,
    "system": False,
    "sender_type": "user"
}

bot.process_message(test_data)
```

**Troubleshooting**
- Bot not responding: Check callback URL
- Messages not storing: Check enable_storage=True
- atexit not firing: Use manual cleanup with bot.destroy()

## Design Principles

1. **Framework Agnostic**: No web framework dependencies
2. **Minimal Configuration**: Environment variables + sensible defaults
3. **Type Safety**: Type hints everywhere
4. **Pythonic API**: Decorators, context managers
5. **Error Handling**: Clear messages, graceful degradation
6. **Single Responsibility**: Bot handles GroupMe, users handle webhooks
7. **Flexibility**: Simple for basic use, powerful for advanced
8. **Storage Optional**: Works with or without persistence

## What This Package Does

✅ Manage GroupMe bot lifecycle (create/destroy)
✅ Route messages to handlers based on commands
✅ Async command execution with threading
✅ Store message history in any SQLAlchemy-compatible database
✅ Send messages with rich media (images, locations)
✅ Support multiple bots per application
✅ Parse GroupMe webhooks into Python objects
✅ Provide SQLAlchemy ORM access for powerful queries
✅ Work seamlessly with Django/Flask databases

## What This Package Does NOT Do

❌ Run a web server
❌ Handle HTTP routing
❌ Provide command argument parsing (keep it simple)
❌ Store state beyond messages
❌ Provide authentication/middleware
❌ Schedule messages or tasks
❌ Implement complex NLP or AI

## Testing Strategy

Write tests for:
- Message model creation from dict, cursor, and query results
- Bot initialization with various configs
- Handler registration and execution
- Command routing (regular, async, unknown)
- Storage operations (save, retrieve, query) with SQLAlchemy
- Testing with different databases (SQLite, mock Postgres)
- Client API calls (mock requests)
- Error handling (missing credentials, API errors, DB errors)
- Multi-bot scenarios
- SQLAlchemy session management and cleanup

Use pytest and mock the requests library and SQLAlchemy where appropriate.

## Success Criteria

The package is successful if a user can:
1. Install with `pip install groupme-bot`
2. Set environment variables
3. Write 15 lines to integrate into any web framework
4. Register handlers with decorators
5. Route commands easily
6. Store and query message history
7. Run multiple bots in one app
8. Send rich media messages

## Key Implementation Notes

- Use `python-dotenv` to support `.env` files
- Use SQLAlchemy 2.0+ for database operations
- Support SQLite, PostgreSQL, MySQL, and any SQLAlchemy-compatible database
- All API calls should have timeouts (10 seconds)
- Message text can be None (for system messages, images, etc.)
- GroupMe uses sender_type "bot" vs "user" to identify source
- Bot should never respond to its own messages
- Multiple handlers can be registered - all execute for each message
- If one handler fails, others should still run
- Commands are checked before regular handlers
- Async commands run in daemon threads
- Only destroy auto-created bots (track with `_auto_created` flag)
- Storage extracts `text` field for queries but keeps full `raw_json`
- Use SQLAlchemy sessions properly with try/finally blocks
- Connection pooling is handled by SQLAlchemy engine
- Table name is `groupme_messages` to avoid conflicts with app tables
- `Message.from_query_results()` expects StoredMessage objects
- `Message.from_cursor()` works with both SQLAlchemy results and raw SQL cursors
- Always close SQLAlchemy sessions after use
- GroupMeSender has no storage - it's purely for sending

## Migration Notes from Old Code

- Review old code for GroupMe API quirks (rate limits, payload formats)
- Keep any working message parsing logic
- Note edge cases (empty messages, special characters, attachments)
- Check for any undocumented API behavior discovered
- Discard web server, framework-specific, or over-engineered code
- Look for any custom storage/query patterns to inform the new design

## Future Enhancements (v2+)

- Async/await support with aiohttp
- More attachment types (videos, files)
- Rate limiting and retry logic
- Structured logging
- Mentions parsing and creation
- Message history fetching from GroupMe API
- Vector embeddings for semantic search
- Command argument parsing helpers
- Bot analytics/metrics

## Development Workflow

1. Implement core classes (models, client, exceptions)
2. Build storage layer
3. Implement GroupMeBot with basic handlers
4. Add command routing
5. Add async command support
6. Implement GroupMeSender
7. Write examples
8. Write tests
9. Write documentation
10. Package and publish

Ready to build! 🚀
"""Simplified GroupMeBot class for sending messages."""

from typing import Dict, Any, Optional
from .client import GroupMeClient
from .storage import MessageStorage


class GroupMeBot:
    """
    Simplified bot class for sending messages.
    Created and managed by GroupMeBotManager.

    This class should not be instantiated directly - use GroupMeBotManager.create_bot() instead.

    Example:
        # Don't do this:
        # bot = GroupMeBot(...)  # Wrong!

        # Do this instead:
        manager = GroupMeBotManager(...)
        bot = manager.create_bot(name="Bean", bot_id="...")
        bot.send_message("Hello!")
    """

    def __init__(
        self,
        bot_id: str,
        name: str,
        client: GroupMeClient,
        group_id: str,
        storage: Optional[MessageStorage] = None,
    ):
        """
        Initialize a bot instance.

        Note: This should only be called by GroupMeBotManager.

        Args:
            bot_id: Bot ID for this bot
            name: Bot name
            client: Shared GroupMeClient instance
            group_id: Group ID this bot belongs to
            storage: Optional shared storage instance
        """
        self.bot_id = bot_id
        self.name = name
        self.client = client
        self.group_id = group_id
        self.storage = storage

        # Update client's bot_id for this bot's operations
        self._original_bot_id = client.bot_id

    def send_message(self, text: str, image_url: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Send a message as this bot.

        Args:
            text: Message text
            image_url: Optional image URL
            **kwargs: Additional arguments passed to client

        Returns:
            Response from GroupMe API
        """
        # Temporarily set client's bot_id to this bot's ID
        original_id = self.client.bot_id
        self.client.bot_id = self.bot_id

        try:
            response = self.client.send_message(text, image_url=image_url, **kwargs)

            # Store sent message if storage is enabled
            if self.storage:
                try:
                    self.storage.save_sent(text, self.group_id, self.bot_id, image_url)
                except Exception as e:
                    print(f"⚠ Failed to store sent message from {self.name}: {e}")

            return response
        except Exception as e:
            print(f"⚠ Failed to send message from {self.name}: {e}")
            raise
        finally:
            # Restore original bot_id
            self.client.bot_id = original_id

    def send_location(self, name: str, lat: float, lng: float, text: str = "") -> Dict[str, Any]:
        """
        Send a location attachment.

        Args:
            name: Location name/label
            lat: Latitude
            lng: Longitude
            text: Optional message text

        Returns:
            Response from GroupMe API
        """
        # Temporarily set client's bot_id to this bot's ID
        original_id = self.client.bot_id
        self.client.bot_id = self.bot_id

        try:
            return self.client.send_location(name, lat, lng, text)
        finally:
            # Restore original bot_id
            self.client.bot_id = original_id

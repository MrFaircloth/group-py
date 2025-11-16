"""Lightweight send-only bot class."""

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

        Raises:
            ConfigurationError: If required credentials are missing
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
        """
        Send a message.

        Args:
            text: Message text
            image_url: Optional image URL
            **kwargs: Additional arguments passed to client

        Returns:
            Response from GroupMe API
        """
        return self.client.send_message(text, image_url=image_url, **kwargs)

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
        return self.client.send_location(name, lat, lng, text)

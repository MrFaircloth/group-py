"""GroupMe API client for bot operations."""

import requests
from typing import Dict, Any, Optional, List
from .exceptions import APIError


class GroupMeClient:
    """Client for interacting with the GroupMe API."""

    BASE_URL = "https://api.groupme.com/v3"

    def __init__(self, api_key: str, bot_id: Optional[str] = None):
        """
        Initialize the GroupMe API client.

        Args:
            api_key: GroupMe API key
            bot_id: Optional bot ID for sending messages
        """
        self.api_key = api_key
        self.bot_id = bot_id
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def create_bot(
        self,
        name: str,
        group_id: str,
        callback_url: str,
        avatar_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new bot in a group.

        Args:
            name: Bot name
            group_id: Group ID where bot will be created
            callback_url: Webhook callback URL
            avatar_url: Optional avatar image URL

        Returns:
            Response dict containing bot info including bot_id

        Raises:
            APIError: If bot creation fails
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
        """
        Delete a bot.

        Args:
            bot_id: Bot ID to destroy

        Raises:
            APIError: If bot destruction fails
        """
        url = f"{self.BASE_URL}/bots/destroy"
        payload = {"bot_id": bot_id}
        params = {"token": self.api_key}

        try:
            response = self.session.post(url, json=payload, params=params, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise APIError(f"Failed to destroy bot: {e}")

    def send_message(
        self,
        text: str,
        image_url: Optional[str] = None,
        attachments: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Send a message as the bot.

        Args:
            text: Message text
            image_url: Optional image URL to attach
            attachments: Optional list of attachment dicts for advanced use

        Returns:
            Response dict from GroupMe API

        Raises:
            APIError: If message sending fails or bot_id not set
        """
        if not self.bot_id:
            raise APIError("Cannot send message: bot_id not set")

        url = f"{self.BASE_URL}/bots/post"
        payload = {"bot_id": self.bot_id, "text": text}

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

        Returns:
            Response dict from GroupMe API
        """
        attachments = [{"type": "location", "lat": str(lat), "lng": str(lng), "name": name}]
        return self.send_message(text or name, attachments=attachments)

    def get_bot_info(self) -> Dict[str, Any]:
        """
        Fetch information about the bot.

        Returns:
            Response dict with bot information

        Raises:
            APIError: If fetching bot info fails
        """
        url = f"{self.BASE_URL}/bots"
        params = {"token": self.api_key}

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise APIError(f"Failed to get bot info: {e}")

    def list_groups(self) -> List[Dict[str, Any]]:
        """
        List all groups the user belongs to.

        Returns:
            List of group dicts

        Raises:
            APIError: If listing groups fails
        """
        url = f"{self.BASE_URL}/groups"
        params = {"token": self.api_key}

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json().get("response", [])
        except requests.exceptions.RequestException as e:
            raise APIError(f"Failed to list groups: {e}")

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
        callback_url: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new bot in a group.

        Args:
            name: Bot name
            group_id: Group ID where bot will be created
            callback_url: Webhook callback URL (optional, only needed for receiving webhooks)
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
                "active": True
            }
        }

        if callback_url:
            payload["bot"]["callback_url"] = callback_url

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

    def _build_mentions_attachment(
        self,
        text: str,
        mentions: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Build mentions attachment with auto-calculated loci.

        Args:
            text: Message text
            mentions: List of {"user_id": "123", "name": "Bob"}

        Returns:
            Mentions attachment dict with format:
            {"type": "mentions", "user_ids": [...], "loci": [[start, length], ...]}

        Example:
            text = "Hey @Bob!"
            mentions = [{"user_id": "123", "name": "Bob"}]
            # Returns: {"type": "mentions", "user_ids": ["123"], "loci": [[4, 4]]}
        """
        user_ids = []
        loci = []

        for mention in mentions:
            name = mention["name"]
            user_id = mention["user_id"]

            # Find @name in text
            search_pattern = f"@{name}"
            index = text.find(search_pattern)

            if index != -1:
                user_ids.append(user_id)
                loci.append([index, len(search_pattern)])

        return {
            "type": "mentions",
            "user_ids": user_ids,
            "loci": loci
        }

    def send_message(
        self,
        text: str,
        image_url: Optional[str] = None,
        attachments: Optional[List[Dict]] = None,
        mentions: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Send a message as the bot.

        Args:
            text: Message text
            image_url: Optional image URL to attach
            attachments: Optional list of attachment dicts for advanced use
            mentions: Optional list of mentions [{"user_id": "123", "name": "Bob"}]

        Returns:
            Response dict with status_code (202 for success, empty body)

        Raises:
            APIError: If message sending fails or bot_id not set

        Example:
            # Send with mentions
            client.send_message(
                "Hey @Bob, check this out!",
                mentions=[{"user_id": "123456", "name": "Bob"}]
            )
        """
        if not self.bot_id:
            raise APIError("Cannot send message: bot_id not set")

        url = f"{self.BASE_URL}/bots/post"
        payload = {"bot_id": self.bot_id, "text": text}

        # Handle image_url shorthand
        if image_url:
            payload["picture_url"] = image_url

        # Build attachments list
        final_attachments = attachments.copy() if attachments else []

        # Add mentions attachment if provided
        if mentions:
            mentions_attachment = self._build_mentions_attachment(text, mentions)
            final_attachments.append(mentions_attachment)

        # Add attachments to payload if any exist
        if final_attachments:
            payload["attachments"] = final_attachments

        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            # GroupMe returns 202 Accepted with empty body for successful sends
            return {"status_code": response.status_code}
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

    def list_bots(self) -> List[Dict[str, Any]]:
        """
        List all bots owned by the user.

        Returns:
            List of bot dicts with bot_id, name, group_id, etc.

        Raises:
            APIError: If listing bots fails

        Example:
            bots = client.list_bots()
            for bot in bots:
                print(f"{bot['name']} in group {bot['group_id']}")
        """
        url = f"{self.BASE_URL}/bots"
        params = {"token": self.api_key}

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json().get("response", [])
        except requests.exceptions.RequestException as e:
            raise APIError(f"Failed to list bots: {e}")

    def find_bot(self, name: str, group_id: str) -> Optional[Dict[str, Any]]:
        """
        Find an existing bot by name and group_id.

        Useful for recovering from crashes - if a bot with the same name
        already exists in the group, we can reuse it instead of creating
        a new orphaned bot.

        Args:
            name: Bot name to search for
            group_id: Group ID the bot should be in

        Returns:
            Bot dict if found, None otherwise

        Example:
            existing = client.find_bot("MyBot", "12345")
            if existing:
                print(f"Found existing bot: {existing['bot_id']}")
        """
        try:
            bots = self.list_bots()
            for bot in bots:
                if bot.get("name") == name and bot.get("group_id") == group_id:
                    return bot
            return None
        except APIError:
            return None

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

    def get_messages(
        self,
        group_id: str,
        limit: int = 100,
        before_id: Optional[str] = None,
        since_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch message history from GroupMe API.

        Args:
            group_id: Group ID to fetch messages from
            limit: Number of messages (max 100 per request)
            before_id: Get messages before this message ID (for pagination)
            since_id: Get messages after this message ID (for backfill)

        Returns:
            List of message dicts (newest first)

        Raises:
            APIError: If request fails

        Example:
            # Get recent messages
            messages = client.get_messages("group_123", limit=50)

            # Paginate
            oldest_id = messages[-1]["id"]
            older = client.get_messages("group_123", limit=50, before_id=oldest_id)
        """
        url = f"{self.BASE_URL}/groups/{group_id}/messages"
        params = {
            "token": self.api_key,
            "limit": min(limit, 100)  # Max 100 per request
        }

        if before_id:
            params["before_id"] = before_id
        if since_id:
            params["since_id"] = since_id

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()["response"]["messages"]
        except requests.exceptions.RequestException as e:
            raise APIError(f"Failed to fetch messages: {e}")

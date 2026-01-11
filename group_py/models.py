"""Data models for GroupMe messages."""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import json


@dataclass
class Message:
    """Represents a GroupMe message from a webhook or database."""

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
    def from_dict(cls, data: dict) -> "Message":
        """
        Parse the GroupMe webhook payload into a Message object.
        Handle missing/optional fields gracefully.

        Args:
            data: Dictionary from GroupMe webhook payload

        Returns:
            Message object
        """
        return cls(
            id=data.get("id", ""),
            text=data.get("text"),
            user_id=data.get("user_id", ""),
            name=data.get("name", "Unknown"),
            group_id=data.get("group_id", ""),
            created_at=data.get("created_at", 0),
            system=data.get("system", False),
            sender_type=data.get("sender_type", "user"),
            avatar_url=data.get("avatar_url"),
            attachments=data.get("attachments", []),
        )


    def has_image(self) -> bool:
        """Check if message contains an image attachment."""
        if not self.attachments:
            return False
        return any(a.get("type") == "image" for a in self.attachments)

    def get_image_url(self) -> Optional[str]:
        """Get the first image URL from attachments."""
        if not self.attachments:
            return None
        for a in self.attachments:
            if a.get("type") == "image":
                return a.get("url")
        return None

    def has_location(self) -> bool:
        """Check if message contains a location attachment."""
        if not self.attachments:
            return False
        return any(a.get("type") == "location" for a in self.attachments)

    def get_location(self) -> Optional[tuple]:
        """Get location as (lat, lng, name) tuple."""
        if not self.attachments:
            return None
        for a in self.attachments:
            if a.get("type") == "location":
                return (a.get("lat"), a.get("lng"), a.get("name"))
        return None

    def reply(self, text: str, **kwargs):
        """
        Reply to this message. This method is injected by the Bot class.
        Will be available after message is processed by bot.

        Args:
            text: Message text to reply with
            **kwargs: Additional arguments passed to send_message()
        """
        raise NotImplementedError("Reply method not initialized")

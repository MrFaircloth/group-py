"""Data models for GroupMe messages."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
import warnings


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

    # Callback injected by bot manager for post() method
    _send_callback: Optional[Callable] = field(default=None, repr=False)

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

    def post(self, text: str, **kwargs):
        """
        Post a message to the group (v3.0+).

        This is the preferred method name in v3.0. It's clearer than "reply"
        since you're not always replying - you're posting to the group.

        Args:
            text: Message text to post
            **kwargs: Additional arguments passed to send_message()
                - image_url: Optional image URL
                - mentions: Optional list of mention dicts
                - attachments: Optional custom attachments

        Returns:
            API response dict

        Raises:
            NotImplementedError: If callback not initialized

        Example:
            @manager.command("hello")
            def hello(message, args):
                message.post("Hello!")

            @manager.command("tag")
            def tag(message, args):
                message.post(
                    f"Hey @{args}!",
                    mentions=[{"user_id": "123", "name": args}]
                )
        """
        if self._send_callback is None:
            raise NotImplementedError(
                "Post method not initialized. This message was not created "
                "by GroupMeBotManager.process_webhook()"
            )
        return self._send_callback(text, **kwargs)

    def reply(self, text: str, **kwargs):
        """
        Reply to this message (DEPRECATED - use post() instead).

        .. deprecated:: 3.0.0
            Use :meth:`post` instead. This method will be removed in v4.0.

        The name "reply" is misleading since you're not always replying to
        something - you're just posting a message to the group.

        Args:
            text: Message text
            **kwargs: Additional arguments passed to post()

        Returns:
            API response dict

        Example (deprecated):
            message.reply("Hello!")  # Shows DeprecationWarning

        Example (recommended):
            message.post("Hello!")
        """
        warnings.warn(
            "Message.reply() is deprecated and will be removed in v4.0. "
            "Use message.post() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.post(text, **kwargs)

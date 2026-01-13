"""
Django ORM models for storing GroupMe messages.

These are OPTIONAL helper models. You can use group-py without them,
or create your own models that better fit your needs.

Example:
    from group_py import GroupMeBotManager
    from group_py.contrib.django.models import GroupMeMessage

    manager = GroupMeBotManager(...)

    @manager.on_any_message
    def store_message(message):
        GroupMeMessage.from_message(message).save()
"""

import json
from django.db import models
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from group_py.models import Message


class GroupMeMessage(models.Model):
    """
    Django model for storing GroupMe messages.

    This model stores the essential fields for querying, plus the full
    raw JSON for complete data access.

    Example:
        # Store a message
        from group_py.contrib.django.models import GroupMeMessage

        @manager.on_any_message
        def store(message):
            GroupMeMessage.from_message(message).save()

        # Query messages
        recent = GroupMeMessage.objects.filter(
            group_id="12345"
        ).order_by('-created_at')[:10]

        # Convert back to Message objects
        messages = [msg.to_message() for msg in recent]
    """

    # Primary key - GroupMe message ID
    message_id = models.CharField(
        max_length=255,
        primary_key=True,
        help_text="GroupMe message ID"
    )

    # Indexed fields for efficient querying
    group_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="GroupMe group ID"
    )
    user_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Sender's user ID"
    )
    created_at = models.IntegerField(
        db_index=True,
        help_text="Unix timestamp when message was created"
    )

    # Searchable/display fields
    user_name = models.CharField(
        max_length=255,
        help_text="Sender's display name"
    )
    text = models.TextField(
        null=True,
        blank=True,
        help_text="Message text content"
    )
    sender_type = models.CharField(
        max_length=20,
        help_text="'user' or 'bot'"
    )
    system = models.BooleanField(
        default=False,
        help_text="Whether this is a system message"
    )
    avatar_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Sender's avatar URL"
    )

    # Full message data for complete access
    raw_json = models.JSONField(
        help_text="Complete message data as JSON"
    )

    class Meta:
        db_table = 'groupme_messages'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['group_id', 'created_at']),
            models.Index(fields=['group_id', 'user_id']),
        ]
        verbose_name = 'GroupMe Message'
        verbose_name_plural = 'GroupMe Messages'

    def __str__(self):
        text_preview = (self.text[:50] + '...') if self.text and len(self.text) > 50 else self.text
        return f"{self.user_name}: {text_preview}"

    @classmethod
    def from_message(cls, message: 'Message') -> 'GroupMeMessage':
        """
        Create a Django model instance from a group-py Message.

        Args:
            message: group-py Message object

        Returns:
            GroupMeMessage instance (not yet saved)

        Example:
            @manager.on_any_message
            def store(message):
                GroupMeMessage.from_message(message).save()
        """
        # Build raw JSON dict
        raw_data = {
            'id': message.id,
            'text': message.text,
            'user_id': message.user_id,
            'name': message.name,
            'group_id': message.group_id,
            'created_at': message.created_at,
            'system': message.system,
            'sender_type': message.sender_type,
            'avatar_url': message.avatar_url,
            'attachments': message.attachments or [],
        }

        return cls(
            message_id=message.id,
            group_id=message.group_id,
            user_id=message.user_id,
            user_name=message.name,
            text=message.text,
            created_at=message.created_at,
            sender_type=message.sender_type,
            system=message.system,
            avatar_url=message.avatar_url,
            raw_json=raw_data,
        )

    def to_message(self) -> 'Message':
        """
        Convert this Django model back to a group-py Message.

        Returns:
            group-py Message object

        Example:
            db_messages = GroupMeMessage.objects.filter(group_id="123")[:10]
            messages = [m.to_message() for m in db_messages]
        """
        from group_py.models import Message
        return Message.from_dict(self.raw_json)


class GroupMeAttachment(models.Model):
    """
    Optional model for storing attachments separately.

    Use this if you want to query attachments independently of messages,
    such as finding all images or locations.

    Example:
        @manager.on_any_message
        def store_with_attachments(message):
            db_msg = GroupMeMessage.from_message(message)
            db_msg.save()

            for att in message.attachments or []:
                GroupMeAttachment.objects.create(
                    message=db_msg,
                    attachment_type=att.get('type', 'unknown'),
                    data=att
                )

        # Find all images
        images = GroupMeAttachment.objects.filter(
            attachment_type='image',
            message__group_id='12345'
        )
    """

    message = models.ForeignKey(
        GroupMeMessage,
        on_delete=models.CASCADE,
        related_name='attachments_set',
        help_text="Parent message"
    )
    attachment_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Attachment type (image, location, etc.)"
    )
    data = models.JSONField(
        help_text="Full attachment data as JSON"
    )

    class Meta:
        db_table = 'groupme_attachments'
        verbose_name = 'GroupMe Attachment'
        verbose_name_plural = 'GroupMe Attachments'

    def __str__(self):
        return f"{self.attachment_type} on {self.message_id}"

    @property
    def url(self):
        """Get URL for image attachments."""
        if self.attachment_type == 'image':
            return self.data.get('url')
        return None

    @property
    def location(self):
        """Get (lat, lng, name) for location attachments."""
        if self.attachment_type == 'location':
            return (
                self.data.get('lat'),
                self.data.get('lng'),
                self.data.get('name'),
            )
        return None

"""Tests for mentions support."""

import pytest
from unittest.mock import Mock, patch
from group_py.client import GroupMeClient


@pytest.fixture
def client_with_bot(mock_api_key, mock_bot_id):
    """Create a GroupMeClient instance with bot_id set."""
    client = GroupMeClient(mock_api_key, bot_id=mock_bot_id)
    return client


class TestMentionsAttachment:
    """Test the _build_mentions_attachment method."""

    def test_single_mention(self, client_with_bot):
        """Test building attachment for a single mention."""
        text = "Hey @Bob, how are you?"
        mentions = [{"user_id": "123456", "name": "Bob"}]

        result = client_with_bot._build_mentions_attachment(text, mentions)

        assert result["type"] == "mentions"
        assert result["user_ids"] == ["123456"]
        assert result["loci"] == [[4, 4]]  # @Bob starts at index 4, length 4

    def test_multiple_mentions(self, client_with_bot):
        """Test building attachment for multiple mentions."""
        text = "Hey @Bob and @Alice, check this out!"
        mentions = [
            {"user_id": "123456", "name": "Bob"},
            {"user_id": "789012", "name": "Alice"}
        ]

        result = client_with_bot._build_mentions_attachment(text, mentions)

        assert result["type"] == "mentions"
        assert result["user_ids"] == ["123456", "789012"]
        assert result["loci"] == [[4, 4], [13, 6]]  # @Bob at 4, @Alice at 13

    def test_mention_not_found(self, client_with_bot):
        """Test that mentions not in text are skipped."""
        text = "Hey everyone!"
        mentions = [{"user_id": "123456", "name": "Bob"}]

        result = client_with_bot._build_mentions_attachment(text, mentions)

        assert result["type"] == "mentions"
        assert result["user_ids"] == []
        assert result["loci"] == []

    def test_partial_mentions(self, client_with_bot):
        """Test mix of found and not found mentions."""
        text = "Hey @Bob!"
        mentions = [
            {"user_id": "123456", "name": "Bob"},
            {"user_id": "789012", "name": "Alice"}  # Not in text
        ]

        result = client_with_bot._build_mentions_attachment(text, mentions)

        assert result["type"] == "mentions"
        assert result["user_ids"] == ["123456"]
        assert result["loci"] == [[4, 4]]

    def test_mention_at_start(self, client_with_bot):
        """Test mention at the beginning of text."""
        text = "@Bob is awesome"
        mentions = [{"user_id": "123456", "name": "Bob"}]

        result = client_with_bot._build_mentions_attachment(text, mentions)

        assert result["type"] == "mentions"
        assert result["user_ids"] == ["123456"]
        assert result["loci"] == [[0, 4]]  # @Bob starts at index 0

    def test_mention_at_end(self, client_with_bot):
        """Test mention at the end of text."""
        text = "Thanks @Bob"
        mentions = [{"user_id": "123456", "name": "Bob"}]

        result = client_with_bot._build_mentions_attachment(text, mentions)

        assert result["type"] == "mentions"
        assert result["user_ids"] == ["123456"]
        assert result["loci"] == [[7, 4]]


class TestSendMessageWithMentions:
    """Test sending messages with mentions."""

    @patch("requests.Session.post")
    def test_send_message_with_single_mention(self, mock_post, client_with_bot):
        """Test sending a message with a single mention."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        text = "Hey @Bob, check this out!"
        mentions = [{"user_id": "123456", "name": "Bob"}]

        result = client_with_bot.send_message(text, mentions=mentions)

        assert result["status_code"] == 202

        # Verify the payload sent to API
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]

        assert payload["text"] == text
        assert payload["bot_id"] == client_with_bot.bot_id
        assert "attachments" in payload
        assert len(payload["attachments"]) == 1
        assert payload["attachments"][0]["type"] == "mentions"
        assert payload["attachments"][0]["user_ids"] == ["123456"]
        assert payload["attachments"][0]["loci"] == [[4, 4]]

    @patch("requests.Session.post")
    def test_send_message_with_multiple_mentions(self, mock_post, client_with_bot):
        """Test sending a message with multiple mentions."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        text = "Hey @Bob and @Alice!"
        mentions = [
            {"user_id": "123456", "name": "Bob"},
            {"user_id": "789012", "name": "Alice"}
        ]

        result = client_with_bot.send_message(text, mentions=mentions)

        assert result["status_code"] == 202

        # Verify mentions attachment
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]

        mentions_attachment = payload["attachments"][0]
        assert mentions_attachment["user_ids"] == ["123456", "789012"]
        assert mentions_attachment["loci"] == [[4, 4], [13, 6]]

    @patch("requests.Session.post")
    def test_send_message_with_mentions_and_image(self, mock_post, client_with_bot):
        """Test sending a message with both mentions and image."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        text = "Hey @Bob, check this image!"
        mentions = [{"user_id": "123456", "name": "Bob"}]
        image_url = "https://example.com/image.jpg"

        result = client_with_bot.send_message(text, image_url=image_url, mentions=mentions)

        assert result["status_code"] == 202

        # Verify both image and mentions are included
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]

        assert payload["picture_url"] == image_url
        assert len(payload["attachments"]) == 1
        assert payload["attachments"][0]["type"] == "mentions"

    @patch("requests.Session.post")
    def test_send_message_with_mentions_and_custom_attachments(self, mock_post, client_with_bot):
        """Test sending a message with mentions and other attachments."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        text = "Hey @Bob, check this location!"
        mentions = [{"user_id": "123456", "name": "Bob"}]
        location_attachment = {
            "type": "location",
            "lat": "37.7749",
            "lng": "-122.4194",
            "name": "San Francisco"
        }

        result = client_with_bot.send_message(
            text,
            mentions=mentions,
            attachments=[location_attachment]
        )

        assert result["status_code"] == 202

        # Verify both location and mentions attachments are included
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]

        assert len(payload["attachments"]) == 2
        assert payload["attachments"][0]["type"] == "location"
        assert payload["attachments"][1]["type"] == "mentions"

    @patch("requests.Session.post")
    def test_send_message_without_mentions(self, mock_post, client_with_bot):
        """Test that normal messages still work without mentions."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        text = "Hello everyone!"

        result = client_with_bot.send_message(text)

        assert result["status_code"] == 202

        # Verify no attachments added when no mentions
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]

        assert payload["text"] == text
        assert "attachments" not in payload

    @patch("requests.Session.post")
    def test_send_message_mentions_not_in_text(self, mock_post, client_with_bot):
        """Test sending mentions when names aren't in text."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        text = "Hello everyone!"
        mentions = [{"user_id": "123456", "name": "Bob"}]  # Bob not in text

        result = client_with_bot.send_message(text, mentions=mentions)

        assert result["status_code"] == 202

        # Verify mentions attachment is still added (even if empty)
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]

        assert len(payload["attachments"]) == 1
        assert payload["attachments"][0]["user_ids"] == []
        assert payload["attachments"][0]["loci"] == []

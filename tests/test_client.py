"""Tests for GroupMeClient."""

import pytest
from unittest.mock import Mock, patch
from group_py.client import GroupMeClient
from group_py.exceptions import APIError


@pytest.fixture
def client(mock_api_key):
    """Create a GroupMeClient instance."""
    return GroupMeClient(mock_api_key)


def test_client_initialization(mock_api_key):
    """Test client initialization."""
    client = GroupMeClient(mock_api_key)
    assert client.api_key == mock_api_key


@patch("requests.post")
def test_create_bot(mock_post, client):
    """Test create_bot method."""
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "response": {"bot": {"bot_id": "new_bot_123", "name": "Test Bot"}}
    }
    mock_post.return_value = mock_response

    result = client.create_bot(
        name="Test Bot", group_id="group_123", callback_url="https://example.com/webhook"
    )

    assert result["bot_id"] == "new_bot_123"
    assert result["name"] == "Test Bot"


@patch("requests.post")
def test_create_bot_api_error(mock_post, client):
    """Test create_bot handles API errors."""
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    mock_post.return_value = mock_response

    with pytest.raises(APIError):
        client.create_bot(
            name="Test Bot", group_id="group_123", callback_url="https://example.com/webhook"
        )


@patch("requests.post")
def test_destroy_bot(mock_post, client):
    """Test destroy_bot method."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    client.destroy_bot("bot_123")

    mock_post.assert_called_once()


@patch("requests.post")
def test_send_message(mock_post, client):
    """Test send_message method."""
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"response": {"message": {"id": "msg_123"}}}
    mock_post.return_value = mock_response

    result = client.send_message("bot_123", "Hello, world!")

    assert result["message"]["id"] == "msg_123"
    mock_post.assert_called_once()


@patch("requests.post")
def test_send_message_with_image(mock_post, client):
    """Test send_message with image_url."""
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"response": {"message": {"id": "msg_123"}}}
    mock_post.return_value = mock_response

    client.send_message("bot_123", "Check this out!", image_url="https://example.com/image.jpg")

    # Verify the call included attachments
    call_args = mock_post.call_args
    json_data = call_args[1]["json"]
    assert "attachments" in json_data["bot"]
    assert json_data["bot"]["attachments"][0]["type"] == "image"


@patch("requests.post")
def test_send_location(mock_post, client):
    """Test send_location method."""
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"response": {"message": {"id": "msg_123"}}}
    mock_post.return_value = mock_response

    client.send_location("bot_123", name="Office", lat=37.7749, lng=-122.4194, text="Meet here!")

    # Verify the call included location attachment
    call_args = mock_post.call_args
    json_data = call_args[1]["json"]
    assert "attachments" in json_data["bot"]
    attachment = json_data["bot"]["attachments"][0]
    assert attachment["type"] == "location"
    assert attachment["lat"] == "37.7749"
    assert attachment["lng"] == "-122.4194"


@patch("requests.get")
def test_list_groups(mock_get, client):
    """Test list_groups method."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": [{"id": "group_1", "name": "Group 1"}, {"id": "group_2", "name": "Group 2"}]
    }
    mock_get.return_value = mock_response

    groups = client.list_groups()

    assert len(groups) == 2
    assert groups[0]["id"] == "group_1"
    assert groups[1]["name"] == "Group 2"


@patch("requests.get")
def test_get_bot_info(mock_get, client):
    """Test get_bot_info method."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": {"bot": {"bot_id": "bot_123", "name": "Test Bot"}}
    }
    mock_get.return_value = mock_response

    info = client.get_bot_info("bot_123")

    assert info["bot_id"] == "bot_123"
    assert info["name"] == "Test Bot"

import pytest
import os


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests against live GroupMe API",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-integration"):
        return

    skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


@pytest.fixture(scope="session")
def live_api_token():
    """Ensures API token is available for integration tests."""
    token = os.getenv("GROUPME_API_TOKEN")
    if not token:
        pytest.skip("GROUPME_API_TOKEN environment variable not set")
    return token


@pytest.fixture(scope="session")
def test_group_id():
    """Test group ID - set via environment variable."""
    group_id = os.getenv("GROUPME_TEST_GROUP_ID")
    if not group_id:
        pytest.skip("GROUPME_TEST_GROUP_ID environment variable not set")
    return group_id


# New fixtures for groupme_bot framework


@pytest.fixture
def mock_api_key():
    """Mock API key for testing."""
    return "test_api_key_12345"


@pytest.fixture
def mock_bot_id():
    """Mock bot ID for testing."""
    return "test_bot_id_67890"


@pytest.fixture
def mock_group_id():
    """Mock group ID for testing."""
    return "test_group_id_11111"


@pytest.fixture
def sample_message_data():
    """Sample GroupMe webhook message data."""
    return {
        "id": "msg_123456",
        "text": "Hello, world!",
        "user_id": "user_123",
        "name": "Test User",
        "group_id": "group_123",
        "created_at": 1234567890,
        "system": False,
        "sender_type": "user",
        "avatar_url": "https://example.com/avatar.jpg",
        "attachments": [],
    }


@pytest.fixture
def sample_message_with_image():
    """Sample message with image attachment."""
    return {
        "id": "msg_123457",
        "text": "Check this out!",
        "user_id": "user_123",
        "name": "Test User",
        "group_id": "group_123",
        "created_at": 1234567891,
        "system": False,
        "sender_type": "user",
        "attachments": [{"type": "image", "url": "https://example.com/image.jpg"}],
    }


@pytest.fixture
def temp_db():
    """Temporary SQLite database for testing."""
    import tempfile

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    connection_string = f"sqlite:///{path}"
    yield connection_string
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


import pytest
import os

def pytest_addoption(parser):
    parser.addoption(
        "--run-integration", 
        action="store_true", 
        default=False, 
        help="run integration tests against live GroupMe API"
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
    token = os.getenv('GROUPME_API_TOKEN')
    if not token:
        pytest.skip("GROUPME_API_TOKEN environment variable not set")
    return token

@pytest.fixture(scope="session") 
def test_group_id():
    """Test group ID - set via environment variable."""
    group_id = os.getenv('GROUPME_TEST_GROUP_ID')
    if not group_id:
        pytest.skip("GROUPME_TEST_GROUP_ID environment variable not set")
    return group_id


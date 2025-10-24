from time import sleep

import pytest
from group_py.api.bots import GroupMeBot

# python -m pytest \
# --run-integration tests/test_bot_integration.py

@pytest.mark.integration
def test_create_bot_for_group(test_group_id, live_api_token):
    """Test creating a bot for a specific group."""
    bot = GroupMeBot(
        name='test-integration-bot',
        group_id=test_group_id,
        avatar_url=None,
        callback_url=None,
        search_for_existing=False  # Force creation of new bot
    )
    
    # Create the bot
    bot_details = bot.create()
    
    # Verify bot was created successfully
    assert bot_details is not None
    assert bot_details['name'] == 'test-integration-bot'
    assert bot_details['group_id'] == test_group_id
    assert bot.bot_id is not None
    
    sleep(0.5)
    # Test bot functionality
    bot.post_message("Hello from integration test!")
    # Cleanup - destroy the bot
    bot.destroy()

    del GroupMeBot._instances[GroupMeBot]



@pytest.mark.integration
def test_find_existing_bot(test_group_id, live_api_token):
    """Test finding an existing bot by name and group."""
    # First create a bot
    bot1 = GroupMeBot(
        name='persistent-test-bot',
        group_id=test_group_id,
        avatar_url=None,
        callback_url=None,
        search_for_existing=False  # Force creation of new bot
    )
    bot1.create()
    bot1_id = bot1.bot_id
    del(bot1)
    sleep(0.5) # Short delay
    
    try:
        # Now try to find it
        bot2 = GroupMeBot(
            name='persistent-test-bot',
            group_id=test_group_id,
            search_for_existing=True
        )
        
        assert bot2.bot_id == bot1_id
        assert bot2.name == 'persistent-test-bot'
        
    finally:
        # Cleanup
        bot2.destroy()
        del GroupMeBot._instances[GroupMeBot]
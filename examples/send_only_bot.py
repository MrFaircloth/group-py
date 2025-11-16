"""
Example: Send-Only Bot (No Webhook Required)

This example shows how to use bots for sending messages only,
without needing to set up a webhook server.

Perfect for:
- Notifications and alerts
- Scheduled messages
- One-way communication
"""

from group_py import GroupMeBotManager

# Option 1: Use existing bot_id (if you already created a bot)
manager = GroupMeBotManager(
    api_key="your_api_key",
    group_id="your_group_id",
    bot_id="your_existing_bot_id",  # Use existing bot
    callback_url="https://example.com/webhook",  # Dummy URL is fine for send-only
)

# Get the primary bot and send messages
bot = manager.primary_bot
bot.send_message("Hello! This is a send-only bot.")
bot.send_message(
    "I can send messages without receiving them!",
    image_url="https://i.groupme.com/123.png"
)


# Option 2: Auto-create bot with dummy callback URL
manager = GroupMeBotManager(
    api_key="your_api_key",
    group_id="your_group_id",
    bot_name="Send Only Bot",
    callback_url="https://example.com/webhook",  # Dummy URL - won't be called
)

bot = manager.primary_bot
bot.send_message("📢 This bot was auto-created!")


# Option 3: Create additional bots for different purposes
notification_bot = manager.create_bot(name="Notifications")
alert_bot = manager.create_bot(name="Alerts")

notification_bot.send_message("📢 This is a notification!")
alert_bot.send_message("🚨 This is an alert!")


# Option 4: Use environment variables
# Set these in your .env file:
# GROUPME_API_KEY=your_key
# GROUPME_GROUP_ID=your_group_id
# GROUPME_BOT_ID=your_bot_id (optional)
# GROUPME_CALLBACK_URL=https://example.com/webhook

from group_py import GroupMeBotManager

manager = GroupMeBotManager()  # Reads from environment
manager.primary_bot.send_message("Configuration from environment variables!")

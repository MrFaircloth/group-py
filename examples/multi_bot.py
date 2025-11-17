"""
Multi-bot example showing one manager with multiple personality bots.

This pattern is useful when you want:
- One manager handling webhooks and command routing
- Multiple "personality" bots that send messages
- All bots sharing the same storage
"""

from flask import Flask, request
from group_py import GroupMeBotManager

# Create manager - this creates the primary webhook bot automatically
manager = GroupMeBotManager(
    api_key="your_api_key",
    group_id="your_group_id",
    callback_url="https://yourserver.com/webhook",
    bot_name="System",
    enable_storage=True,
)

# Get the primary bot for sending system messages
system_bot = manager.primary_bot

# Create additional personality bots (all share storage automatically!)
bean_bot = manager.create_bot(name="Bean", bot_id="bean_bot_id")
coffee_bot = manager.create_bot(name="Coffee")  # Will auto-create if no bot_id


# Manager handles all commands
@manager.command("/bean")
def bean_command(message, args):
    """Make Bean say something."""
    bean_bot.send_message(f"🫘 Bean says: {args}")


@manager.command("/coffee")
def coffee_command(message, args):
    """Make Coffee bot say something."""
    coffee_bot.send_message(f"☕ Coffee says: {args}")


@manager.command("/status")
def status_command(message, args):
    """Check bot status."""
    recent = manager.get_recent_messages(limit=10)
    message.reply(f"📊 Last {len(recent)} messages stored")


@manager.command("/help")
def help_command(message, args):
    """Show available commands."""
    help_text = """
Available commands:
/bean <message> - Make Bean say something
/coffee <message> - Make Coffee say something
/status - Show message statistics
/help - Show this help message
    """.strip()
    message.reply(help_text)


# Regular message handling
@manager.on_message
def handle_regular(message):
    """Handle regular messages."""
    if message.has_image():
        bean_bot.send_message("🖼️ Nice image!")


# Flask setup
app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle GroupMe webhook."""
    manager.process_webhook(request.get_json())
    return "ok", 200


@app.route("/health")
def health():
    """Health check."""
    return {
        "status": "ok",
        "system_bot": system_bot.bot_id,
        "bean_bot": bean_bot.bot_id,
        "coffee_bot": coffee_bot.bot_id,
    }


if __name__ == "__main__":
    print(f"🤖 System bot: {system_bot.bot_id}")
    print(f"🫘 Bean bot: {bean_bot.bot_id}")
    print(f"☕ Coffee bot: {coffee_bot.bot_id}")
    app.run(port=3000)

"""
Multi-bot example showing one bot handling webhooks and another sending messages.

This pattern is useful when you want:
- One "system" bot that handles commands and webhooks
- Additional "personality" bots that only send messages
"""

from flask import Flask, request
from groupme_bot import GroupMeBot, GroupMeSender

# Main bot - handles webhooks
system_bot = GroupMeBot(
    group_id="your_group_id",
    callback_url="https://yourserver.com/webhook",
    bot_name="System",
    enable_storage=True,
)

# Secondary bot - only sends messages
bean_bot = GroupMeSender(
    bot_id="bean_bot_id",
    api_key="your_api_key",
)


# System bot handles commands
@system_bot.command("/bean")
def bean_command(message, args):
    """Make Bean say something."""
    bean_bot.send_message(f"🫘 Bean says: {args}")


@system_bot.command("/status")
def status_command(message, args):
    """Check bot status."""
    recent = system_bot.get_recent_messages(limit=10)
    message.reply(f"📊 Last {len(recent)} messages stored")


@system_bot.command("/help")
def help_command(message, args):
    """Show available commands."""
    help_text = """
Available commands:
/bean <message> - Make Bean say something
/status - Show message statistics
/help - Show this help message
    """.strip()
    message.reply(help_text)


# Regular message handling
@system_bot.on_message
def handle_regular(message):
    """Handle regular messages."""
    if message.has_image():
        bean_bot.send_message("🖼️ Nice image!")


# Flask setup
app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle GroupMe webhook."""
    system_bot.process_message(request.get_json())
    return "ok", 200


@app.route("/health")
def health():
    """Health check."""
    return {
        "status": "ok",
        "system_bot": system_bot.bot_id,
        "bean_bot": bean_bot.bot_id,
    }


if __name__ == "__main__":
    print(f"🤖 System bot: {system_bot.bot_id}")
    print(f"🫘 Bean bot: {bean_bot.bot_id}")
    app.run(port=3000)

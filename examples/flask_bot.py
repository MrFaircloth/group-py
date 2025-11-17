"""Flask integration example with commands, storage, and async handlers."""

from flask import Flask, request
from group_py import GroupMeBotManager

# Initialize manager - creates primary bot automatically
manager = GroupMeBotManager(
    api_key="your_api_key",
    group_id="your_group_id",
    callback_url="https://yourserver.com/groupme-webhook",
    bot_name="Flask Bot",
    enable_storage=True,
)

# Get primary bot for sending messages
bot = manager.primary_bot


# Command: /prompt - sends to LLM (async example)
@manager.async_command("/prompt", ack_message="🤔 Thinking...")
def handle_prompt(message, args):
    """Handle LLM prompts with context."""
    import time

    # Get conversation context
    context = manager.get_recent_messages(limit=20, as_objects=True)
    context_text = "\n".join([f"{m.name}: {m.text}" for m in reversed(context) if m.text])

    # Simulate LLM call
    time.sleep(2)
    response = f"Response to: {args}\n\nContext used: {len(context)} messages"

    message.reply(response)


# Command: /search - search message history
@manager.command("/search")
def handle_search(message, args):
    """Search message history."""
    from group_py.storage import StoredMessage

    session = manager.get_db_session()
    try:
        results = (
            session.query(StoredMessage)
            .filter(StoredMessage.text.like(f"%{args}%"))
            .order_by(StoredMessage.created_at.desc())
            .limit(10)
            .all()
        )

        from group_py import Message

        messages = Message.from_query_results(results)

        if messages:
            summary = f"Found {len(messages)} messages:\n"
            for msg in messages[:3]:
                summary += f"• {msg.name}: {msg.text[:50]}...\n"
            message.reply(summary)
        else:
            message.reply(f"No messages found matching '{args}'")
    finally:
        session.close()


# Command: /stats - show bot statistics
@manager.command("/stats")
def handle_stats(message, args):
    """Show message statistics."""
    from group_py.storage import StoredMessage
    from sqlalchemy import func

    session = manager.get_db_session()
    try:
        total = session.query(func.count(StoredMessage.id)).scalar()
        message.reply(f"📊 Total messages stored: {total}")
    finally:
        session.close()


# Unknown command handler
@manager.on_unknown_command
def handle_unknown(message, command_text):
    """Handle unknown commands."""
    message.reply(f"❓ Unknown command. Try:\n/prompt <text>\n/search <query>\n/stats")


# Catch-all for regular messages
@manager.on_message
def handle_message(message):
    """Handle regular messages."""
    if message.text and "hello" in message.text.lower():
        message.reply("👋 Hi there!")


# Create Flask app
app = Flask(__name__)


@app.route("/groupme-webhook", methods=["POST"])
def webhook():
    """Handle GroupMe webhook callbacks."""
    data = request.get_json()
    manager.process_webhook(data)
    return "ok", 200


@app.route("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "bot_id": bot.bot_id}


if __name__ == "__main__":
    print(f"🤖 Bot running with ID: {bot.bot_id}")
    app.run(port=3000, debug=True)

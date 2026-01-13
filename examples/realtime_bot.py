"""
Example: Real-time WebSocket bot (no webhook needed).

This bot connects via WebSocket to receive messages in real-time.
No need to expose an HTTP endpoint or configure webhooks!

Requirements:
    - GROUPME_API_KEY: Your GroupMe API key
    - GROUPME_GROUP_ID: The group ID to listen to
    - GROUPME_USER_ID: Your GroupMe user ID (required for WebSocket)

Usage:
    export GROUPME_API_KEY="your_api_key"
    export GROUPME_GROUP_ID="your_group_id"
    export GROUPME_USER_ID="your_user_id"
    python realtime_bot.py
"""

import os
from group_py import GroupMeBotManager


def main():
    # Create manager with realtime enabled
    manager = GroupMeBotManager(
        api_key=os.getenv("GROUPME_API_KEY"),
        group_id=os.getenv("GROUPME_GROUP_ID"),
        user_id=os.getenv("GROUPME_USER_ID"),
        enable_realtime=True,
        bot_name="RealtimeBot",
    )

    print("Real-time bot connected via WebSocket - no webhook needed!")

    # Log all messages
    @manager.on_any_message
    def log_all(message):
        print(f"[{message.name}]: {message.text}")

    # Simple greeting command
    @manager.command("hello")
    def hello(message, args):
        name = args if args else message.name
        message.post(f"Hello, {name}!")

    # Echo command
    @manager.command("echo")
    def echo(message, args):
        if args:
            message.post(args)
        else:
            message.post("Usage: echo <message>")

    # Time command
    @manager.command("time")
    def time_cmd(message, args):
        from datetime import datetime
        now = datetime.now().strftime("%I:%M %p")
        message.post(f"Current time: {now}")

    # Help command
    @manager.command("help")
    def help_cmd(message, args):
        message.post(
            "Available commands:\n"
            "  hello [name] - Say hello\n"
            "  echo <text> - Echo back text\n"
            "  time - Show current time\n"
            "  help - Show this help"
        )

    # Handle unknown commands
    @manager.on_unknown_command
    def unknown(message, command_text):
        message.post(f"Unknown command: {command_text}. Try 'help' for available commands.")

    # Keep the program running
    print("\nBot is running... Press Ctrl+C to stop")
    print("Try sending 'hello', 'echo test', 'time', or 'help' in the group!")

    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        if manager.realtime_manager:
            manager.realtime_manager.stop()
        print("Bot stopped.")


if __name__ == "__main__":
    main()

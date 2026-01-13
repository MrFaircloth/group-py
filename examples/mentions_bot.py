"""
Example: Bot with @mentions support.

group-py v3.0+ has built-in support for @mentions. The library automatically
calculates the correct loci (character positions) for mentions, which is
required by the GroupMe API.

Usage:
    export GROUPME_API_KEY="your_api_key"
    export GROUPME_GROUP_ID="your_group_id"
    export GROUPME_USER_ID="your_user_id"  # Optional, for realtime mode
    python mentions_bot.py
"""

import os
from group_py import GroupMeBotManager


def main():
    manager = GroupMeBotManager(
        api_key=os.getenv("GROUPME_API_KEY"),
        group_id=os.getenv("GROUPME_GROUP_ID"),
        user_id=os.getenv("GROUPME_USER_ID"),
        enable_realtime=bool(os.getenv("GROUPME_USER_ID")),
        bot_name="MentionBot",
    )

    print("Mentions bot ready!")

    # Command to mention someone
    @manager.command("tag")
    def tag_user(message, args):
        """Tag a user by name. Usage: tag <user_id> <name>"""
        parts = args.split(" ", 1)
        if len(parts) < 2:
            message.post("Usage: tag <user_id> <display_name>")
            return

        user_id, name = parts

        # The mentions parameter automatically calculates loci
        message.post(
            f"Hey @{name}, you've been tagged!",
            mentions=[{"user_id": user_id, "name": name}]
        )

    # Command to mention everyone who sent a message
    @manager.command("shoutout")
    def shoutout(message, args):
        """Give a shoutout to the message sender."""
        sender_name = message.name
        sender_id = message.user_id

        message.post(
            f"Shoutout to @{sender_name} for being awesome!",
            mentions=[{"user_id": sender_id, "name": sender_name}]
        )

    # Multiple mentions in one message
    @manager.command("tagall")
    def tag_multiple(message, args):
        """Demo multiple mentions."""
        # In a real bot, you might fetch group members from the API
        # This is just a demonstration of the syntax
        message.post(
            "Multiple mentions work too: @Alice and @Bob",
            mentions=[
                {"user_id": "alice_id", "name": "Alice"},
                {"user_id": "bob_id", "name": "Bob"},
            ]
        )

    # Using mentions with images
    @manager.command("tagphoto")
    def tag_with_photo(message, args):
        """Mention with an image."""
        sender_name = message.name
        sender_id = message.user_id

        message.post(
            f"Here's something for you, @{sender_name}!",
            mentions=[{"user_id": sender_id, "name": sender_name}],
            image_url="https://i.groupme.com/someimage.png"  # Replace with real image
        )

    @manager.command("help")
    def help_cmd(message, args):
        message.post(
            "Mention commands:\n"
            "  tag <user_id> <name> - Tag a specific user\n"
            "  shoutout - Get a shoutout with @mention\n"
            "  tagall - Demo multiple mentions\n"
            "  help - Show this help"
        )

    # Keep running if in realtime mode
    if manager.realtime_manager:
        print("Running in realtime mode... Press Ctrl+C to stop")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            manager.realtime_manager.stop()
    else:
        print("Use with Flask/Django webhook, or set GROUPME_USER_ID for realtime")


if __name__ == "__main__":
    main()

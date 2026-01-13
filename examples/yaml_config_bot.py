"""
Example: Bot configured via YAML file.

group-py v3.0+ supports YAML configuration files for cleaner bot setup.
This example shows how to use YAML config instead of hardcoding credentials.

Usage:
    1. Copy bots.yaml.example to bots.yaml
    2. Fill in your credentials
    3. Run: python yaml_config_bot.py
"""

from group_py import GroupMeBotManager


def main():
    # Load configuration from YAML file
    # The manager will look for groupme_config.yaml by default,
    # or you can specify a custom path
    manager = GroupMeBotManager.from_yaml("bots.yaml")

    print("Bot loaded from YAML configuration!")

    # All the usual decorators work the same way
    @manager.on_any_message
    def log_message(message):
        print(f"[{message.name}]: {message.text}")

    @manager.command("ping")
    def ping(message, args):
        message.post("Pong!")

    @manager.command("info")
    def info(message, args):
        message.post(
            f"Bot: {manager.primary_bot.name}\n"
            f"Group: {manager.group_id}"
        )

    # If realtime is enabled in the YAML, the bot is already connected!
    if manager.realtime_manager:
        print("Real-time mode enabled via YAML config")
        print("Bot is running... Press Ctrl+C to stop")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            manager.realtime_manager.stop()
    else:
        print("Webhook mode - use this with your web framework")
        print("See flask_bot.py for an example")


if __name__ == "__main__":
    main()

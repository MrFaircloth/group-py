"""
Example: Using Django models to store GroupMe messages.

This example shows how to integrate group-py with Django for message
persistence. The Django models provide optional storage that can be
used alongside your own application models.

Setup:
    1. Install with Django support: pip install group-py[django]
    2. Add 'group_py.contrib.django' to INSTALLED_APPS in settings.py
    3. Run migrations: python manage.py migrate

Usage:
    This can be run as a Django management command or integrated
    into your Django application.
"""

import os
import django

# Configure Django settings (in a real app, this would be in settings.py)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

# For standalone example, configure minimal settings
if not django.conf.settings.configured:
    django.conf.settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': 'groupme_messages.db',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'group_py.contrib.django',
        ],
        DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
    )

django.setup()

from django.core.management import call_command
from group_py import GroupMeClient, GroupMeBotManager
from group_py.contrib.django.models import GroupMeMessage, GroupMeAttachment


def setup_database():
    """Run migrations to create tables."""
    print("Running migrations...")
    call_command('migrate', '--run-syncdb', verbosity=1)
    print("Database ready!")


def store_message(message):
    """
    Store a message in the database.

    This function can be used as a handler for @manager.on_any_message.
    """
    # Convert to Django model and save
    db_msg = GroupMeMessage.from_message(message)
    db_msg.save()

    # Optionally store attachments separately for querying
    for att in message.attachments or []:
        GroupMeAttachment.objects.create(
            message=db_msg,
            attachment_type=att.get('type', 'unknown'),
            data=att
        )

    print(f"Stored message: {message.id}")


def query_recent_messages(group_id: str, limit: int = 10):
    """Query recent messages from a group."""
    messages = GroupMeMessage.objects.filter(
        group_id=group_id
    ).order_by('-created_at')[:limit]

    return [msg.to_message() for msg in messages]


def query_messages_by_user(user_id: str, group_id: str = None):
    """Query all messages from a specific user."""
    queryset = GroupMeMessage.objects.filter(user_id=user_id)
    if group_id:
        queryset = queryset.filter(group_id=group_id)
    return queryset.order_by('-created_at')


def query_images(group_id: str = None):
    """Find all image attachments."""
    queryset = GroupMeAttachment.objects.filter(attachment_type='image')
    if group_id:
        queryset = queryset.filter(message__group_id=group_id)
    return queryset


def search_messages(text: str, group_id: str = None):
    """Search messages containing text."""
    queryset = GroupMeMessage.objects.filter(text__icontains=text)
    if group_id:
        queryset = queryset.filter(group_id=group_id)
    return queryset.order_by('-created_at')


# Example: Full bot with message storage
def run_bot_with_storage():
    """Run a bot that stores all messages."""
    api_key = os.getenv('GROUPME_API_KEY')
    group_id = os.getenv('GROUPME_GROUP_ID')

    if not api_key or not group_id:
        print("Set GROUPME_API_KEY and GROUPME_GROUP_ID environment variables")
        return

    # Set up database
    setup_database()

    # Create bot manager
    client = GroupMeClient(api_key)
    manager = GroupMeBotManager(client, group_id)

    # Store all messages
    @manager.on_any_message
    def on_message(message):
        store_message(message)

    # Add a command to search stored messages
    @manager.command("search")
    def search_cmd(message, args):
        if not args:
            return "Usage: !search <text>"

        results = search_messages(args, group_id)[:5]
        if not results:
            return f"No messages found containing '{args}'"

        lines = [f"Found {results.count()} messages:"]
        for msg in results[:5]:
            lines.append(f"- {msg.user_name}: {msg.text[:50]}...")
        return "\n".join(lines)

    # Add a command to show recent messages
    @manager.command("recent")
    def recent_cmd(message, args):
        limit = int(args) if args.isdigit() else 5
        messages = query_recent_messages(group_id, limit)

        lines = [f"Last {len(messages)} messages:"]
        for msg in messages:
            lines.append(f"- {msg.name}: {msg.text[:30] if msg.text else '[attachment]'}...")
        return "\n".join(lines)

    print(f"Bot running, storing messages to database...")
    print(f"Commands: !search <text>, !recent [count]")

    # Start real-time listening
    manager.run()


# Example: Backfill historical messages
def backfill_history(group_id: str, count: int = 100):
    """Fetch and store historical messages."""
    api_key = os.getenv('GROUPME_API_KEY')
    if not api_key:
        print("Set GROUPME_API_KEY environment variable")
        return

    setup_database()

    client = GroupMeClient(api_key)
    messages = client.get_group_messages(group_id, limit=count)

    stored = 0
    for msg in messages:
        # Check if already stored
        if not GroupMeMessage.objects.filter(message_id=msg.id).exists():
            store_message(msg)
            stored += 1

    print(f"Stored {stored} new messages (skipped {len(messages) - stored} existing)")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == 'backfill':
            group_id = sys.argv[2] if len(sys.argv) > 2 else os.getenv('GROUPME_GROUP_ID')
            count = int(sys.argv[3]) if len(sys.argv) > 3 else 100
            backfill_history(group_id, count)
        elif sys.argv[1] == 'run':
            run_bot_with_storage()
        else:
            print("Usage: python django_storage.py [backfill|run]")
    else:
        print("Django Storage Example")
        print("=" * 40)
        print("\nCommands:")
        print("  python django_storage.py run      - Run bot with storage")
        print("  python django_storage.py backfill - Store historical messages")
        print("\nRequired environment variables:")
        print("  GROUPME_API_KEY")
        print("  GROUPME_GROUP_ID")

"""
Optional Django integration for group-py.

Provides Django ORM models for storing GroupMe messages. These are OPTIONAL
helper models - you don't need them to use group-py.

Installation:
    1. Install: pip install group-py[django]
    2. Add to INSTALLED_APPS: 'group_py.contrib.django'
    3. Run migrations: python manage.py migrate group_py_django
    4. Use @on_any_message to store messages

Example:
    from group_py import GroupMeBotManager
    from group_py.contrib.django.models import GroupMeMessage

    manager = GroupMeBotManager(...)

    @manager.on_any_message
    def store_message(message):
        GroupMeMessage.from_message(message).save()

    # Query stored messages
    recent = GroupMeMessage.objects.filter(
        group_id="12345"
    ).order_by('-created_at')[:10]
"""

default_app_config = 'group_py.contrib.django.apps.GroupPyDjangoConfig'

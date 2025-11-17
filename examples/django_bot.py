"""
Django integration example.

This example shows how to integrate the GroupMe bot manager with Django,
including using Django's database for message storage.

File structure:
    myapp/
        bot_instance.py  # Bot configuration (this file)
        views.py         # View handlers
        urls.py          # URL routing
"""

# ============================================================================
# bot_instance.py - Create manager instance once
# ============================================================================

from group_py import GroupMeBotManager
from django.conf import settings

# Build SQLAlchemy connection string from Django database settings
db = settings.DATABASES["default"]
engine = db["ENGINE"]

if "postgresql" in engine:
    connection_string = (
        f"postgresql://{db['USER']}:{db['PASSWORD']}@{db['HOST']}:{db['PORT']}/{db['NAME']}"
    )
elif "mysql" in engine:
    connection_string = (
        f"mysql://{db['USER']}:{db['PASSWORD']}@{db['HOST']}:{db['PORT']}/{db['NAME']}"
    )
else:
    # Fallback to SQLite
    connection_string = f"sqlite:///{db['NAME']}"

manager = GroupMeBotManager(
    enable_storage=True,
    storage_connection=connection_string,  # Use Django's database!
)

# Get primary bot for sending messages
bot = manager.primary_bot


@manager.command("/echo")
def handle_echo(message, args):
    """Echo command."""
    message.reply(f"You said: {args}")


@manager.on_message
def handle_message(message):
    """Handle regular messages."""
    if message.text and "hello" in message.text.lower():
        message.reply("Hi from Django!")


# ============================================================================
# views.py
# ============================================================================

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

# from .bot_instance import manager


@method_decorator(csrf_exempt, name="dispatch")
class GroupMeWebhook(View):
    """Handle GroupMe webhook callbacks."""

    def post(self, request):
        """Process incoming webhook."""
        data = json.loads(request.body)
        manager.process_webhook(data)
        return JsonResponse({"ok": True})


# ============================================================================
# urls.py
# ============================================================================

from django.urls import path

# from .views import GroupMeWebhook

urlpatterns = [
    path("groupme-webhook/", GroupMeWebhook.as_view()),
]

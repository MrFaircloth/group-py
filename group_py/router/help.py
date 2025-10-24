from .groupme_message import Message
from .handlers import CommandHandler
from ..api.bots import GroupMeBot

class HelpHandler(CommandHandler):

    def command():
        return '!help'

    def help():
        return (
            "\tCollects all commands and prints functionality."
        )

    def can_handle(message: Message):
        return message.text.lower().strip().startswith('!help')

    def execute(message: Message):
        # Bot and Router MUST be instatiated
        from .router import MessageRouter
        bot = GroupMeBot()
        router = MessageRouter()

        commands = []
        for route in router.get_routes.values():
            if issubclass(route.handler, CommandHandler):
                commands.append(
                    f'{route.handler.command()}\n'
                    f'{route.handler.help()}\n'
                )

        bot.post_message('\n'.join(commands))
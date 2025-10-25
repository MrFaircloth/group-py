from typing import TYPE_CHECKING

from .groupme_message import Message
from .handlers import CommandHandler

if TYPE_CHECKING:
    from .context import HandlerContext


class HelpHandler(CommandHandler):
    command_str = '!help'

    @classmethod
    def command(cls):
        return cls.command_str

    @staticmethod
    def help():
        return "Collects all commands and prints functionality."

    @classmethod
    def can_handle(cls, message: Message):
        return message.text.lower().strip().startswith(cls.command_str)

    def execute(context: 'HandlerContext'):
        commands = ['-- Commands -- ']
        for route in context.router.get_routes.values():
            if issubclass(route.handler, CommandHandler):
                commands.append(
                    f'> {route.handler.command()}: '
                    f'{route.handler.help()}'
                )

        context.bot.post_message('\n'.join(commands))
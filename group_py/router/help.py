from group_py import GroupMeBot, Message, CommandHandler, MessageRouter

class helpHandler(CommandHandler):

    def command():
        return '!help'

    def help():
        return (
            "Collects all commands and prints functionality."
        )

    def can_handle(message: Message):
        return message.text.lower().strip().startswith('!help')
    
    def execute(message: Message):
        # Bot and Router MUST be instatiated
        bot = GroupMeBot()
        router = MessageRouter()

        commands = []
        for route in router.get_routes.values():
            if issubclass(route.handler, CommandHandler):
                commands.append(
                    f'{route.handler.command}\n'
                    f'{route.handler.help()}'
                )

        bot.post_message('\n'.join(commands))
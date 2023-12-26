from group_py import GroupMeBot, Message, CommandHandler

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
        bot = GroupMeBot()
        # TODO - Get router somehow
        # post to group
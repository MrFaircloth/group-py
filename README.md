# group-py
Groupme API Handler

## Purpose
This module is to be used to simplify interactions with the GroupMe API.


### Authentication
Groupme API can be accessed with the Users API Token.
[See the Groupme Developers documenation](https://dev.groupme.com/). The API token can be found at the top right by your username. 

All of these commands assume the user has the required permissions for their groups.

The access token can be set using the `GROUPME_API_TOKEN` environment variable.


### Message Router
The callback handler module can be used to route and handle messages based on their contents.
For example, in the context of a flask app:

```
from group_py.callback_handler import MessageHandler, MessageRouter

class ReadyHandler(MessageHandler):
    def can_handle(message: Message) -> bool:
        '''
        Checks message contents for handler criteria.
        '''
        return message.text.lower().strip() == '!ready'

    def execute(message: Message) -> None:
        '''Executes action based on given input.'''
        ... do some action ...
        return {'ready': True }

router = MessageRouter([ReadyHandler])

@app.route('/callback', methods=['POST'])
def callback():
    raw_message_data: dict = request.get_json()
    message = Message(raw_message_data)
    result = router.route(message)
    return result
```

We can create a ReadyHandler object which will then be routed to by the router if the message contexts fits the criteria of the Handlers `can_handle` function. 


### Bots
Bots can be managed using the bot module.

```
from group_py.api.bots import GroupMeBot

bot = GroupMeBot(
    name='test_bot',
    group_id='1234567890'
    bot_id= '1234567890',
    group_id= '1234567890',
    name= 'test_bot',
    avatar_url= 'https://i.groupme.com/123456789',
    callback_url= 'https://example.com/bots/callback',
    dm_notification= false,
    active= true
)
bot_details = bot.create() # creates bot and adds to group
# returns all relevant bot details
# {
#   'bot_id': '1234567890',
#   'group_id': '1234567890',
#   'name': 'test_bot',
#   'avatar_url': 'https://i.groupme.com/123456789',
#   'callback_url': 'https://example.com/bots/callback',
#   'dm_notification': false,
#   'active': true
# }

bot.post_message('this is a message') # posts message to group
bot.destroy() # destroys bot and removes from group

```

 You can also create a bot object using an existing bot by providing the ID. On init, the if `bot_id` is provided, the GroupMe API will check for that bot and automatically assign the rest of the values.

 ```
 from group_py.api.bots import GroupMeBot

bot = GroupMeBot(bot_id='1234567890')
bot.post_message( ... )
 ```

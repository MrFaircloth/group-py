import logging

from api import groupme_api, GroupmeBotError


class GROUPME_BOT:
    def __init__(
        self,
        bot_id: str = None,
        name: str = None,
        group_id: str = None,
        avatar_url: str = None,
        callback_url: str = None,
        dm_notification: bool = None,
        active: bool = True,
    ):
        if bot_id:
            self.index(self, bot_id)
        else:
            if not all(name, group_id):
                raise TypeError(
                    'Parameters "name" and "group_id" are required if "bot_id" is not defined.'
                )
            self.name = name
            self.group_id = group_id
            self.avatar_url = avatar_url
            self.callback_url = callback_url
            self.dm_notification = dm_notification
            self.active = active

    def create(self):
        ''' Creates bot in configured GroupMe group. '''
        # https://dev.groupme.com/docs/v3#bots_create
        data = {
            'name': self.name,
            'group_id': self.group_id,
            'avatar_url': self.avatar_url,
            'callback_url': self.callback_url,
            'dm_notification': self.dm_notification,
            'active': self.active,
        }

        bot_details = groupme_api('POST', '/bots', data=data)
        self.bot_id = bot_details['bot_id']
        return bot_details

    def index(self, bot_id: str) -> dict:
        ''' Searches for matching bot ID and updates object details. '''
        index_data = groupme_api('GET', '/bots')
        filtered_data: list = filter(
            lambda person: person['bot_id'] == bot_id, index_data
        )

        if len(filtered_data):
            bot_data = filtered_data[0]  # should be only one element
            self.name = bot_data['name']
            self.group_id = bot_data['group_id']
            self.avatar_url = bot_data['avatar_url']
            self.callback_url = bot_data['callback_url']
            self.dm_notification = bot_data['dm_notification']
            self.active = bot_data['active']
            return bot_data
        raise GroupmeBotError(f'Unable to find GroupMe bot with ID "{bot_id}"')


    def destroy(self):
        # https://dev.groupme.com/docs/v3#bots_destroy
        groupme_api('POST', '/bots/destroy', {'bot_id': self.bot_id})


    def post_message(self, text: str, picture_url: str = None):
        # https://dev.groupme.com/docs/v3#bots_post
        groupme_api('POST', '/bots/post', {'text': text, 'picture_url': picture_url})


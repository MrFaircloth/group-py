import logging
from threading import Lock

from .api import groupme_api, GroupmeBotError

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('GroupMeBot')


def index():
    #  https://dev.groupme.com/docs/v3#bots_index
    response = groupme_api('GET', path=f'/bots')
    if response.ok:
        return response.json()['response']


class SingletonMeta(type):
    """
    A thread-safe implementation of Singleton.
    """

    _instances = {}
    _lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
            return cls._instances[cls]


class GroupMeBot(metaclass=SingletonMeta):
    def __init__(
        self,
        bot_id: str = None,
        name: str = None,
        group_id: str = None,
        avatar_url: str = '',
        callback_url: str = '',
        dm_notification: bool = False,
        active: bool = True,
        search_for_existing: bool = True,
    ):
        if bot_id:
            self.bot_id = bot_id
            logger.info(f'Checking for existing bot id "{bot_id}"')
            self.index(bot_id)
        else:
            if not all((name, group_id)):
                raise TypeError(
                    'Parameters "name" and "group_id" are required if "bot_id" is not defined.'
                )
            if search_for_existing:
                try:
                    self.index(bot_name=name, group_id=group_id)
                except GroupmeBotError:
                    pass
            self.name = name
            self.group_id = group_id
            self.avatar_url = avatar_url
            self.callback_url = callback_url
            self.dm_notification = dm_notification
            self.active = active

    def create(self, force: bool = False) -> dict:
        '''Creates bot in configured GroupMe group.'''
        # https://dev.groupme.com/docs/v3#bots_create
        if self.bot_id:
            logger.info('Bot already assigned.')
            return
        data = {
            'bot': {
                'name': self.name,
                'group_id': self.group_id,
                'avatar_url': self.avatar_url,
                'callback_url': self.callback_url,
                'dm_notification': self.dm_notification,
                'active': self.active,
            }
        }
        logger.info(f'Creating bot {self.name}.')
        bot_details = groupme_api('POST', '/bots', data=data).json()['response']['bot']
        self.bot_id = bot_details['bot_id']
        logger.info(f'Successfully created bot. ID "{self.bot_id}"')
        return bot_details

    def update_bot(self, bot_data):
        self.bot_id = bot_data['bot_id']
        self.name = bot_data['name']
        self.group_id = bot_data['group_id']
        self.avatar_url = bot_data['avatar_url']
        self.callback_url = bot_data['callback_url']
        self.dm_notification = bot_data['dm_notification']
        self.active = bot_data['active']
        return bot_data

    def index(self, bot_id: str = None, bot_name: str = None, group_id: str = None) -> dict:
        '''Searches for matching bot ID / name & group and updates object details.'''
        logger.info('Fetching existing bots...')
        index_data = index()
        filtered_data: list = list(
            filter(
                lambda bot: 
                bot['bot_id'] == bot_id or
                bot['name'] == bot_name and
                bot['group_id'] == group_id, 
                index_data)
        )
        if len(filtered_data):
            logger.info(f'Found bot matching ID "{bot_id}"')
            return self.update_bot(filtered_data[0])
        raise GroupmeBotError(f'Unable to find GroupMe bot.')

    def destroy(self):
        # https://dev.groupme.com/docs/v3#bots_destroy
        if hasattr(self, 'bot_id'):
            logger.info(f'Destroying bot ID "{self.bot_id}"')
            groupme_api('POST', '/bots/destroy', {'bot_id': self.bot_id})

    def post_message(self, text: str, picture_url: str = None):
        # https://dev.groupme.com/docs/v3#bots_post
        logger.info(f'Posting message "{text}"')
        message_data = {'bot_id': self.bot_id, 'text': text, 'picture_url': picture_url}
        groupme_api('POST', '/bots/post', data=message_data)

from api import groupme_api_post


def create(
    name: str,
    group_id: str,
    avatar_url: str = None,
    callback_url: str = None,
    dm_notification: bool = None,
    active: bool = True,
):
    # https://dev.groupme.com/docs/v3#bots_create
    params = {
        'name': name,
        'group_id': group_id,
        'avatar_url': avatar_url,
        'callback_url': callback_url,
        'dm_notification': dm_notification,
        'active': active,
    }
    groupme_api_post('/bots', params=params)
    return params


# TODO
def destroy():
    # https://dev.groupme.com/docs/v3#bots_destroy
    pass


def index():
    # https://dev.groupme.com/docs/v3#bots_index
    pass


def post_message():
    # https://dev.groupme.com/docs/v3#bots_post
    pass

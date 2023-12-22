# https://dev.groupme.com/docs/v3#message
from uuid import uuid4

from api import groupme_api


def index(
    group_id: str,
    before_id: str = None,
    since_id: str = None,
    after_id: str = None,
    limit: int = 20,
) -> dict:
    # https://dev.groupme.com/docs/v3#messages_index
    params = {
        'before_id': before_id,
        'since_id': since_id,
        'after_id': after_id,
    }
    if sum(1 for param in params.values() if param is not None) != 1:
        raise ValueError("Exactly one id condition parameter should be set")
    params['limit'] = limit
    return groupme_api('GET', f'/groups/{group_id}/messages', params=params).json()


def message(group_id: str, text: str = None, attachments: list = []) -> dict:
    # https://dev.groupme.com/docs/v3#messages_create
    # /groups/:group_id/messages
    data = {
        'source_uuid': uuid4(),
        'text': text,
        'attachments': attachments,
    }
    return groupme_api('POST', f'/groups/{group_id}/messages', data=data)
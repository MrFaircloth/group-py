

from api import groupme_api_get

def groupme_groups_index(page: int = 1, per_page: int = 10):

    params = {
        'page': page,
        'per_page': per_page,
    }
    response = groupme_api_get(path='/groups', params=params)
    return response

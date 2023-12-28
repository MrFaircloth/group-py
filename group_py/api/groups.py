from .api import groupme_api


def groupme_groups_index(page: int = 1, per_page: int = 10):
    # https://dev.groupme.com/docs/v3#groups_index
    params = {
        'page': page,
        'per_page': per_page,
    }
    response = groupme_api('GET', path='/groups', params=params)
    return response

def groupme_groups_show(id: str):
    #  https://dev.groupme.com/docs/v3#groups_show
    response = groupme_api('GET', path=f'/groups/{id}')
    return response


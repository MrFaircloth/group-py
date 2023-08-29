from typing import TypeAlias, Literal
import os
import requests

from .util import param_filter

API_TOKEN = os.getenv('GROUPME_API_TOKEN')

Method: TypeAlias = Literal['GET', 'POST']

class GroupmeBotError(Exception):
    '''Custom bot exception.'''


def groupme_api(method: Method, path: str, params: dict = {}, data: dict = {}) -> dict:
    '''Handles GroupMe api requests.'''
    url = f'https://api.groupme.com/v3{path}'
    params['token'] = API_TOKEN

    params = param_filter(params)

    if method.upper() == 'GET':
        response = requests.get(url, params=params)

    elif method.upper() == 'POST':
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, params=params, json=data, headers=headers)

    else:
        raise ValueError("Invalid HTTP method. Use 'GET' or 'POST'.")

    if response.status_code in range(200, 300):
        return response

    raise (GroupmeBotError(f"API Error {response.status_code}: {response.json()}"))

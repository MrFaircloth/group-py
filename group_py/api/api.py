import os
import requests

from helpers import param_filter

API_TOKEN = os.getenv('GROUPME_API_TOKEN')

class GroupmeBotError(Exception):
    ''' Custom bot exception. '''


def groupme_api(method: str, path: str, params: dict = {}, data: dict = {}) -> dict:
    ''' Handles GroupMe api requests. '''
    url = f'https://api.groupme.com/v3{path}'
    params['token'] = API_TOKEN

    params = param_filter(params)

    if method.upper() == 'GET':
        response = requests.get(url, params=params)
    elif method.upper() == 'POST':
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=data, headers=headers)
    else:
        raise ValueError("Invalid HTTP method. Use 'GET' or 'POST'.")
    
    if response.status_code == 200:
        return response.json()
    
    raise(GroupmeBotError(f"API Error: {response.status_code}"))

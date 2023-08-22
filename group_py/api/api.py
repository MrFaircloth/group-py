import os
import requests

from helpers import param_filter

TOKEN = os.getenv('GROUPME_API_TOKEN')

# TODO: One funtion to rule them all.

def groupme_api_get(path: str, params: dict = {}):
    url = f'https://api.groupme.com/v3{path}'
    params['token'] = TOKEN

    params = param_filter(params)

    response = requests.get(url, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return False


def groupme_api_post(path: str, params: dict = {}):
    url = f'https://api.groupme.com/v3{path}'
    headers = {'Content-Type': 'application/json'}
    params['token'] = TOKEN

    data = param_filter(params)

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return False

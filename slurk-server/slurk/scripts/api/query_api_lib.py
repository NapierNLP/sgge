import json
import requests
from scripts.api.api_lib_config import ADMIN_TOKEN, API_URL

DEFAULT_HEADERS = {
    "Authorization": f"Bearer {ADMIN_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
                   }


def check_response(response_json):
    if 'code' in response_json:
        raise ValueError(f"Unexpected API Response:\n{response_json}")
    else:
        return response_json


def api_call(method, endpoint, params=None, data_json=None):
    if params is None:
        params = {}
    if data_json is None:
        data_json = {}
    response = requests.request(method,
                                API_URL + f"/{endpoint}",
                                headers=DEFAULT_HEADERS,
                                params=params,
                                json=data_json)
    try:
        json_response = json.loads(response.content)
        verified_response = check_response(json_response)
        return verified_response
    except ValueError:
        if json_response['code'] == 404:
            raise ValueError(f"404 - endpoint not found: {endpoint}")



def query_api(endpoint, params=None, data_json=None):
    return api_call("GET", endpoint, params, data_json)


def submit_api(endpoint, params=None, data_json=None):
    return api_call("POST", endpoint, params, data_json)

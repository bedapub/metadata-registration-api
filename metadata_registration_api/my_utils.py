import yaml
import os
from pathlib import Path
import requests


def load_credentials(filename=".credentials.yaml"):
    """" Load credential from file. """
    try:
        # Navigate to project root directory
        location = Path(__file__).parents[1]
        path = os.path.join(location, filename)
        with open(path, 'r') as f:
            credentials = yaml.load(f, Loader=yaml.SafeLoader)
            return credentials
    except IOError:
        print("Could not find credentials file. Credentials are expected to be in the project root directory.")
        raise


def map_key_value(url, key="id", value="name"):
    """Call API at url endpoint and create a dict which maps key to value

    If the response contains identical keys, only the last value is stored for this key. The mapping only works
    for fields in the top level (no nested fields).

    :param url: API endpoint to call
    :type url: str
    :param key: The key by which the value will be found
    :type key: str
    :param value: The value to which the key will map
    :type value: str
    ...
    :return: A dict with maps key -> value
    :rtype: dict

    """
    res = requests.get(url, headers={"x-Fields": f"{key}, {value}"})

    if res.status_code != 200:
        raise Exception(f"Request to {url} failed with key: {key} and value: {value}. {res.json()}")

    return {entry[key]: entry[value] for entry in res.json()}

"""Utility function used for only testing"""

import requests
from urllib.parse import urljoin


def clear_collections(entry_point, routes=None, complete=True):
    """ Remove all entries"""

    for route in routes:
        url = urljoin(entry_point, route)
        res = requests.delete(url=url, params={"complete": complete})

        if res.status_code != 200:
            raise Exception(f"Could not delete {url}. {res.json()}")


def get_ids(endpoint="localhost", deprecated=False):
    """ Get the id of all properties """
    return requests.get(ulr=f"{endpoint}?deprecated={deprecated}",
                        headers={"X-Fields": "id"},
                        )


def insert(url=None, data=None):
    """ Insert a new entry """
    res = requests.post(url=url, json=data)

    if res.status_code != 201:
        raise Exception(f"Could not insert entry into {url}. {res.json()}")

    return res

from dataclasses import dataclass
from datetime import datetime
import os
import requests
from typing import Optional
from urllib.parse import urljoin

from flask import current_app as app

from metadata_registration_lib.api_utils import map_key_value


@dataclass()
class ChangeLog:
    action: str
    user_id: str
    timestamp: datetime
    manual_user: Optional[str] = None

    def to_dict(self):
        return {key: value for key, value in self.__dict__.items() if value}


class MetaInformation:
    def __init__(self, state: str, change_log=None):

        if change_log and not isinstance(change_log, list):
            raise AttributeError("Change log has to be an instance of list")

        self.state = state
        self.change_log = change_log if change_log else list()

    def add_log(self, log: ChangeLog):
        self.change_log.append(log.to_dict())

    def to_json(self):
        return {"state": self.state, "change_log": self.change_log}


def get_json(url, headers={}):
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        raise Exception(f"Request to {url} failed. {res.json()}")

    return res.json()


def get_property_map(key, value, mask=None):
    """ Helper to get property mapper """
    property_url = urljoin(app.config["URL"], os.environ["API_EP_PROPERTY"])
    property_map = map_key_value(
        url=f"{property_url}?deprecated=true", key=key, value=value, mask=mask
    )
    return property_map


def get_cv_items_map(key="name", value="label"):
    """
    Returns a map to find the CV item labels in this format:
    {cv_name: {item_name: item_label}}
    """
    cv_url = urljoin(app.config["URL"], os.environ["API_EP_CTRL_VOC"])

    res = requests.get(f"{cv_url}/map_items")

    if res.status_code != 200:
        raise Exception(
            f"Request to {cv_url} failed with key: {key} and value: {value}. {res.json()}"
        )

    return res.json()

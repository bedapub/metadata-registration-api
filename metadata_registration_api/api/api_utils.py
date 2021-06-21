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


def get_property_map(key, value):
    """ Helper to get property mapper """
    property_url = urljoin(app.config["URL"], os.environ["API_EP_PROPERTY"])
    property_map = map_key_value(
        url=f"{property_url}?deprecated=true", key=key, value=value
    )
    return property_map


def get_cv_items_name_to_label_map():
    """
    Returns a map to find the CV item labels in this format:
    {cv_name: {item_name: item_label}}
    """
    cv_url = urljoin(app.config["URL"], os.environ["API_EP_CTRL_VOC"])
    cv_map = map_key_value(cv_url, key="name", value="items")
    cv_items_map = {}
    for cv_name, cv_items in cv_map.items():
        cv_items_map[cv_name] = {item["name"]: item["label"] for item in cv_items}

    return cv_items_map
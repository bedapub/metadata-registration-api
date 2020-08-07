"""Utility function used for only testing"""

import requests

from metadata_registration_api import my_utils


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

import logging
import os
from threading import Thread
from werkzeug.serving import make_server
from metadata_registration_api.app import create_app

logger = logging.getLogger(__name__)


class ServerThread(Thread):
    
    def __init__(self, config="TESTING"):
        super(ServerThread, self).__init__()

        app = create_app(config=config)
        self.config = app.config

        self.srv = make_server(os.environ["API_HOST"], os.environ["PORT"], app)

        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        super(ServerThread, self).run()
        logger.info("Start API Server")
        self.srv.serve_forever()

    def shutdown(self):
        self.srv.shutdown()
        logger.info("Stop API Server")


if __name__ == '__main__':

    server = ServerThread()
    server.run()
    server.shutdown()

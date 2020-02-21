from threading import Thread
import time
import os
from urllib.parse import urljoin

import unittest

from metadata_registration_api.app import create_app
from metadata_registration_api import my_utils


class BaseTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        CONFIG = "TESTING"
        app = create_app(config=CONFIG)
        cls.config = app.config
        cls.credentials = my_utils.load_credentials()[CONFIG]

        cls.host = "http://" + os.environ["API_HOST"] + ":" + str(os.environ["PORT"])

        cls.ctrl_voc_endpoint = urljoin(cls.host, cls.credentials["api"]["endpoint"]["ctrl_vocs"])
        cls.property_endpoint = urljoin(cls.host, cls.credentials["api"]["endpoint"]["properties"])
        cls.form_endpoint = urljoin(cls.host, cls.credentials["api"]["endpoint"]["forms"])
        cls.study_endpoint = urljoin(cls.host, cls.credentials["api"]["endpoint"]["studies"])

        def run_api(app):
            app.run(threaded=True, port=5001)

        cls.thread = Thread(target=run_api, args=(app, ))
        cls.thread.setDaemon(True)
        cls.thread.start()
        # time.sleep(0.8)

    # @classmethod
    # def tearDownClass(cls) -> None:
    #     cls.thread.join(timeout=0.1)


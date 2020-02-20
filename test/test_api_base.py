from threading import Thread
import time
import os

import unittest

from metadata_registration_api.app import create_app


class BaseTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        app = create_app(config="TESTING")
        cls.config = app.config
        cls.host = "http://" + ":".join(("127.0.0.1", "5001"))

        def run_api(app):
            app.run(threaded=True, port=5001)

        cls.thread = Thread(target=run_api, args=(app, ))
        cls.thread.setDaemon(True)
        cls.thread.start()
        time.sleep(0.8)

    # @classmethod
    # def tearDownClass(cls) -> None:
    #     cls.thread.join(timeout=0.1)


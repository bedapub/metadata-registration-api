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
        cls.host = "http://" + ":".join([os.environ["API_HOST"], os.environ["PORT"]])

        def run_api(app):
            app.run(threaded=True, port=int(os.environ["PORT"]))

        cls.thread = Thread(target=run_api, args=(app, ))
        cls.thread.setDaemon(True)
        cls.thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.thread.join(timeout=0.1)


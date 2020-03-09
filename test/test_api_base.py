from threading import Thread
from flask import request
import time
import os
from urllib.parse import urljoin
import requests
import unittest

from metadata_registration_api.app import create_app
from metadata_registration_api import my_utils


class BaseTestCase(unittest.TestCase):
    """Run the WSGI server in separate daemon thread"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.config_type = cls.config_type if hasattr(cls, "config_type") else "TESTING"

        cls.app = create_app(config=cls.config_type)

        def shutdown():
            if "werkzeug.server.shutdown" not in request.environ:
                raise RuntimeError("Is not a WSGI server")
            request.environ.get("werkzeug.server.shutdown")()
            return "Shutdown server"

        cls.app.add_url_rule("/shutdown", "shutdown", view_func=shutdown)

        cls.config = cls.app.config
        cls.credentials = my_utils.load_credentials()[cls.config_type]

        # Create host
        cls.host = "http://" + os.environ["API_HOST"] + ":" + str(os.environ["PORT"])

        # Create API endpoints
        cls.ctrl_voc_endpoint = urljoin(cls.host, cls.credentials["api"]["endpoint"]["ctrl_vocs"])
        cls.property_endpoint = urljoin(cls.host, cls.credentials["api"]["endpoint"]["properties"])
        cls.form_endpoint = urljoin(cls.host, cls.credentials["api"]["endpoint"]["forms"])
        cls.study_endpoint = urljoin(cls.host, cls.credentials["api"]["endpoint"]["studies"])
        cls.user_endpoint = urljoin(cls.host, cls.credentials["api"]["endpoint"]["users"])

        cls.shutdown_endpoint = urljoin(cls.host, "shutdown")

        def run_api(app):
            app.run(threaded=True, port=os.environ["PORT"])

        cls.thread = Thread(target=run_api, args=(cls.app, ), daemon=cls).start()
        time.sleep(0.5)


    @classmethod
    def tearDownClass(cls) -> None:
        requests.get(cls.shutdown_endpoint)


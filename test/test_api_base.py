from threading import Thread
from flask import request
import time
import os
from urllib.parse import urljoin
import requests
import unittest

from metadata_registration_api.app import create_app


class BaseTestCase(unittest.TestCase):
    """Run the WSGI server in separate daemon thread"""

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["FLASK_DEBUG"] = "0"
        os.environ["FLASK_ENV"] = "development"
        os.environ["APP_SECRET"] = "secret_for_testing"
        os.environ["CHECK_ACCESS_TOKEN"] = "false"
        os.environ["PORT"] = "5001"
        os.environ["API_HOST"] = "127.0.0.1"
        os.environ["API_EP_CTRL_VOC"] = "/ctrl_voc"
        os.environ["API_EP_PROPERTY"] = "/properties"
        os.environ["API_EP_FORM"] = "/forms"
        os.environ["API_EP_STUDY"] = "/studies"
        os.environ["API_EP_USER"] = "/users"
        os.environ["MONGODB_DB"] = "test_metadata_api_dev"
        os.environ["MONGODB_HOST"] = "localhost"
        os.environ["MONGODB_PORT"] = "27017"
        os.environ["MONGODB_USERNAME"] = ""
        os.environ["MONGODB_PASSWORD"] = ""
        os.environ["MONGODB_COL_PROPERTY"] = "testing_metadata_api_properties"
        os.environ["MONGODB_COL_CTRL_VOC"] = "testing_metadata_api_ctrl_voc"
        os.environ["MONGODB_COL_FORM"] = "testing_metadata_api_form"
        os.environ["MONGODB_COL_USER"] = "testing_metadata_api_user"
        os.environ["MONGODB_COL_STUDY"] = "testing_metadata_api_study"

        cls.app = create_app()
        cls.app.testing = True

        def shutdown():
            if "werkzeug.server.shutdown" not in request.environ:
                raise RuntimeError("Is not a WSGI server")
            request.environ.get("werkzeug.server.shutdown")()
            return "Shutdown server"

        cls.app.add_url_rule("/shutdown", "shutdown", view_func=shutdown)

        cls.config = cls.app.config

        # Create host
        cls.host = cls.config["URL"]

        # Create API endpoints
        cls.ctrl_voc_endpoint = urljoin(cls.host, os.environ["API_EP_CTRL_VOC"])
        cls.property_endpoint = urljoin(cls.host, os.environ["API_EP_PROPERTY"])
        cls.form_endpoint = urljoin(cls.host, os.environ["API_EP_FORM"])
        cls.study_endpoint = urljoin(cls.host, os.environ["API_EP_STUDY"])
        cls.user_endpoint = urljoin(cls.host, os.environ["API_EP_USER"])

        cls.shutdown_endpoint = urljoin(cls.host, "shutdown")

        def run_api(app):
            app.run(threaded=True, port=os.environ["PORT"])

        cls.thread = Thread(target=run_api, args=(cls.app,), daemon=cls).start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls) -> None:
        requests.get(cls.shutdown_endpoint)
        time.sleep(0.5)

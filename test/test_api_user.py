import time

import requests
from urllib.parse import urljoin
import unittest

from metadata_registration_api.errors import TokenException
from test.test_api_base import BaseTestCase
from scripts import setup

from dynamic_form.template_builder import UserTemplate


# @unittest.skip
class MyTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(MyTestCase, cls).setUpClass()
        cls.route = "users"
        cls.url = urljoin(cls.host, cls.route)

    def setUp(self) -> None:
        setup.clear_collection(self.user_endpoint)

    # ------------------------------------------------------------------------------------------------------------------
    # POST & GET

    def test_add_user(self):

        res = self.insert_one()

        res = requests.get(url=self.user_endpoint + f"/id/{res.json()['id']}")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 6)

    # ------------------------------------------------------------------------------------------------------------------
    # PUT

    def test_update_password(self):
        res = self.insert_one()

        data = {"password": "new_password"}

        res = requests.put(url=self.url + f"/id/{res.json()['id']}", json=data)

        self.assertEqual(res.status_code, 200)

    def test_login(self):
        self.insert_one()

        data = {
            "email": "jane.doe@email.com",
            "password": "unhashed"
        }

        res = requests.post(url=urljoin(self.url, "users/login"), json=data)

        self.assertEqual(res.status_code, 200)
        self.assertTrue("X-Access-Token" in res.json().keys())

    # ------------------------------------------------------------------------------------------------------------------
    # Helper function

    def insert_one(self):
        firstname, lastname, email, password = "Jane", "Doe", "jane.doe@email.com", "unhashed"

        data = UserTemplate(firstname, lastname, email, password)
        res = requests.post(url=self.url, json=data.to_dict())

        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(res.json()), 2)

        return res


class AuthorizationTest(BaseTestCase):
    """Check access control"""
    
    @classmethod
    def setUpClass(cls) -> None:
        cls.config_type = "TESTING_SECURE"
        super(AuthorizationTest, cls).setUpClass()

    def test_post_without_token(self):

        for endpoint in [self.ctrl_voc_endpoint, self.property_endpoint, self.form_endpoint, self.study_endpoint,
                         self.user_endpoint]:

            res = requests.post(endpoint)

            self.assertEqual(res.status_code, 401, f"Fail {endpoint}")
            self.assertEqual(res.json()['error type'], TokenException.__name__, f"Fail {endpoint}")

    def test_post_invalid_token(self):
        for endpooint in [self.ctrl_voc_endpoint]:
            res = requests.post(endpooint, headers={"X-Access-Token": "unknown"})

            self.assertEqual(res.status_code, 401, f"Fail {endpooint}")
            self.assertEqual(res.json()["error type"], TokenException.__name__)

    def test_delete_without_token(self):

        for endpoint in [self.ctrl_voc_endpoint, self.property_endpoint, self.form_endpoint, self.study_endpoint,
                         self.user_endpoint]:

            res = requests.delete(endpoint)

            self.assertEqual(res.status_code, 401, f"Fail {endpoint}")
            self.assertEqual("TokenException", res.json()['error type'], f"Fail {endpoint}")

    def test_put_without_token(self):

        for endpoint in [self.ctrl_voc_endpoint, self.property_endpoint, self.form_endpoint, self.study_endpoint,
                         self.user_endpoint]:

            res = requests.put(endpoint + "/id/1")

            self.assertEqual(res.status_code, 401, f"Fail {endpoint}")
            self.assertEqual("TokenException", res.json()['error type'], f"Fail {endpoint}")

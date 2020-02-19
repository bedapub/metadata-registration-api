import requests
from urllib.parse import urljoin
import unittest

from test.test_api_base import BaseTestCase
from test import test_utils

from dynamic_form.template_builder import UserTemplate


@unittest.skip
class MyTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(MyTestCase, cls).setUpClass()
        cls.route = "users"
        cls.url = urljoin(cls.host, cls.route)

    def setUp(self) -> None:
        test_utils.clear_collections(entry_point=self.host, routes=[self.route])

    # ------------------------------------------------------------------------------------------------------------------
    # POST & GET

    def test_add_user(self):

        res = self.insert_one()

        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(res.json()), 2)

        res = requests.get(url=self.url + f"/id/{res.json()['id']}")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 6)

    # ------------------------------------------------------------------------------------------------------------------
    # PUT

    def test_update_password(self):
        res = self.insert_one()

        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(res.json()), 2)

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
        self.assertTrue("x-access-token" in res.json().keys())

    # ------------------------------------------------------------------------------------------------------------------
    # Access control

    @unittest.skip
    def test_post_without_token(self):
        check_access_token = self.config['CHECK_ACCESS_TOKEN']
        self.config['CHECK_ACCESS_TOKEN'] = True

        for entrypoint in ["/ctrl_vocs/", "/properties/", "/forms", "/studies/", self.route]:
            # TODO: Only works if get request needs access token
            res = requests.get(urljoin(self.host, entrypoint))

            self.assertTrue("error type" in res.json())
            self.assertEqual("TokenException", res.json()['error type'], f"Failed with {entrypoint}")

        self.config['CHECK_ACCESS_TOKEN'] = check_access_token

    # ------------------------------------------------------------------------------------------------------------------
    # Helper function

    def insert_one(self):
        firstname, lastname, email, password = "Jane", "Doe", "jane.doe@email.com", "unhashed"

        data = UserTemplate(firstname, lastname, email, password)
        return requests.post(url=self.url, json=data.to_dict())

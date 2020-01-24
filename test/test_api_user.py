import unittest

from test.test_api_base import AbstractTest
from metadata_registration_api.app import create_app


class MyTestCase(unittest.TestCase, AbstractTest):

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app(config="TESTING").test_client()
        cls.clear_collection()

    def setUp(self) -> None:
        MyTestCase.clear_collection()
        MyTestCase.clear_collection(entrypoint="/users/")

    # ------------------------------------------------------------------------------------------------------------------
    # POST & GET

    def test_add_user(self):
        firstname, lastname, email, password = "Jane", "Doe", "jane.doe@email.com", "unhashed"

        res = MyTestCase.insert_one(firstname, lastname, email, password)
        res = MyTestCase.get(MyTestCase.app, entrypoint=f"users/id/{res.json['id']}")

        self.assertEqual(res.json['firstname'], firstname)
        self.assertEqual(res.json['lastname'], lastname)
        self.assertEqual(res.json['email'], email)
        self.assertEqual(res.json['is_active'], True)
        self.assertNotEqual(res.json['password'], password)  # Password is hashed

    # ------------------------------------------------------------------------------------------------------------------
    # PUT

    def test_update_user(self):
        firstname, lastname, email, password = "Jane", "Doe", "jane.doe@email.com", "unhashed"
        new_password = "password 2"

        res = MyTestCase.insert_one(firstname, lastname, email, password)

        data = {
            "password": new_password
        }

        res = MyTestCase.app.put(f"/users/id/{res.json['id']}", json=data, follow_redirects=True)

        self.assertEqual(res.status_code, 200)

    def test_login(self):
        firstname, lastname, email, password = "Jane", "Doe", "jane.doe@email.com", "unhashed"

        MyTestCase.insert_one(firstname, lastname, email, password)

        data = {
            "email": email,
            "password": password
        }

        res = MyTestCase.app.post("/users/login", json=data)

        self.assertEqual(res.status_code, 200)
        self.assertTrue("x-access-token" in res.json.keys())

    # ------------------------------------------------------------------------------------------------------------------
    # Access control

    def test_post_without_token(self):
        check_access_token = MyTestCase.app.application.config['CHECK_ACCESS_TOKEN']
        MyTestCase.app.application.config['CHECK_ACCESS_TOKEN'] = True

        for entrypoint in ["/ctrl_vocs/", "/properties/", "/forms/", "/studies/", "/users/"]:
            res = MyTestCase.app.post(entrypoint, follow_redirects=True)

            self.assertTrue("error type" in res.json)
            self.assertEqual("TokenException", res.json['error type'])

        MyTestCase.app.application.config['CHECK_ACCESS_TOKEN'] = check_access_token

    @staticmethod
    def insert_one(firstname, lastname, email, password):
        data = {
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
            "password": password,
        }

        return MyTestCase.insert(MyTestCase.app, entrypoint="/users/", data=data)

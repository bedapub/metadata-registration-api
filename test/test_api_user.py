import unittest

from test.test_api_base import AbstractTest
from api_service.app import create_app


class MyTestCase(unittest.TestCase, AbstractTest):


    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app(config="TESTING").test_client()
        cls.clear_collection()

    def setUp(self) -> None:
        MyTestCase.clear_collection()
        MyTestCase.clear_collection(entrypoint="/user/")

    def test_add_user(self):
        firstname, lastname, email, password = "Jane", "Doe", "jane.doe@email.com", "unhashed"

        res = MyTestCase.insert_one(firstname, lastname, email, password)
        res = MyTestCase.get(MyTestCase.app, entrypoint=f"user/id/{res.json['id']}")

        self.assertEqual(res.json['firstname'], firstname)
        self.assertEqual(res.json['lastname'], lastname)
        self.assertEqual(res.json['email'], email)
        self.assertEqual(res.json['is_active'], True)
        self.assertNotEqual(res.json['password'], password) # Password is hashed

    def test_verify_email(self):
        firstname, lastname, email, password = "Jane", "Doe", "jane.doe@email.com", "unhashed"
        res = MyTestCase.insert_one(firstname, lastname, email, password)

        data = {"email": email}

        res = MyTestCase.app.post("user/email/", json=data)

        self.assertEqual(res.json['firstname'], firstname)
        self.assertEqual(res.json['lastname'], lastname)
        self.assertEqual(res.json['email'], email)
        self.assertEqual(res.json['is_active'], True)




    @staticmethod
    def insert_one(firstname, lastname, email, password):

        data = {
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
            "password": password,
        }

        return MyTestCase.insert(MyTestCase.app, entrypoint="/user/", data=data)



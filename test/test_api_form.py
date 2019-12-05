import unittest

from api_service.app import create_app
from test.test_api_base import AbstractTest


class MyTestCase(unittest.TestCase, AbstractTest):

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app(config="TESTING").test_client()
        AbstractTest.clear_collection(cls.app)

    def setUp(self) -> None:
        MyTestCase.clear_collection(MyTestCase.app)
        MyTestCase.clear_collection(MyTestCase.app, entrypoint="/ctrl_voc")
        MyTestCase.clear_collection(MyTestCase.app, entrypoint="/form")

    # ------------------------------------------------------------------------------------------------------------------
    # GET

    def test_form_(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    # POST

    def test_add_form(self):

        prop_data = {
            "label": "Username",
            "name": "username",
            "level": "top",
            "vocabulary_type": {"data_type": "text"},
            "description": "Recognizable name"
        }

        prop_res = MyTestCase.insert(MyTestCase.app, data=prop_data,entrypoint="/properties")

        form_data = {
            "label": "Login",
            "name": "login",
            "description": "Form to login a user",
            "fields": [
                {"property_id": prop_res.json['id'],
                 "kwargs": {'validation': {'args': {'object': {'class_name': 'InputRequired'}}}}}
            ],
        }

        form_res = MyTestCase.insert(MyTestCase.app, data=form_data, entrypoint="/form")

        self.assertEqual(form_res.status_code, 201)




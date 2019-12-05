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

        prop_user_data = {
            "label": "Username",
            "name": "username",
            "level": "top",
            "vocabulary_type": {"data_type": "text"},
            "description": "Recognizable name"
        }

        prop_pw_data = {
            "label": "Password",
            "name": "password",
            "level": "top",
            "vocabulary_type": {"data_type": "text"},
            "description": "Secret to authenticate user"
        }

        prop_user_res = MyTestCase.insert(MyTestCase.app, data=prop_user_data,entrypoint="/properties")
        prop_pw_res = MyTestCase.insert(MyTestCase.app, data=prop_pw_data,entrypoint="/properties")

        form_data = {
            "label": "Login",
            "name": "login",
            "description": "Form to login a user",
            "fields": [
                {"label": "Username",
                 "property": prop_user_res.json['id'],
                 "metadata": {'class_name': 'StringField'},
                 "kwargs": [{'validators': {'args': {'objects': [{'class_name': 'InputRequired'}]}}}]
                 },
                {"label": "Password",
                 "property": prop_pw_res.json["id"],
                 "metadata": {'class_name': 'PasswordField'},
                 "kwargs": [{'validators': {'args': {'objects': [
                     {'class_name': 'InputRequired'},
                     {'class_name': 'Length', 'args': {'min': 8, 'max': 64}}]}}}]
                }
            ],
        }

        form_res = MyTestCase.insert(MyTestCase.app, data=form_data, entrypoint="/form")

        self.assertEqual(form_res.status_code, 201)




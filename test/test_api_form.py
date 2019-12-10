import unittest

from api_service.app import create_app
from test.test_api_base import AbstractTest


class MyTestCase(unittest.TestCase, AbstractTest):

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app(config="TESTING").test_client()
        cls.clear_collection()

    def setUp(self) -> None:
        MyTestCase.clear_collection()
        MyTestCase.clear_collection(entrypoint="/ctrl_voc/")
        MyTestCase.clear_collection(entrypoint="/form/")

    # ------------------------------------------------------------------------------------------------------------------
    # GET

    def test_retrieve_login_form(self):
        self.clear_collection()
        self.insert_login_form()
        res = self.app.get("/form/", follow_redirects=True)
        form = res.json

    # ------------------------------------------------------------------------------------------------------------------
    # POST

    def test_add_login_form(self):

        res = self.insert_login_form(

        )

        self.assertEqual(res.status_code, 201)

    def insert_login_form(self):

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

        prop_user_res = self.insert(self.app, data=prop_user_data,entrypoint="/properties/")
        prop_pw_res = self.insert(self.app, data=prop_pw_data,entrypoint="/properties/")

        form_data = {
            "label": "Login",
            "name": "login",
            "description": "Form to login a user",
            "fields": [
                {"label": "Username",
                 "property": prop_user_res.json['id'],
                 'class_name': 'StringField',
                 "kwargs": {'validators': {'kwargs': {'objects': [{'class_name': 'InputRequired'}]}}}
                 },
                {"label": "Password",
                 "property": prop_pw_res.json["id"],
                 'class_name': 'PasswordField',
                 "kwargs": {'validators': {'args': {'objects': [
                     {'class_name': 'InputRequired'},
                     {'class_name': 'Length', 'kwargs': {'min': 8, 'max': 64}}]}}}
                 }
            ],
        }

        return self.insert(self.app, data=form_data, entrypoint="/form/")



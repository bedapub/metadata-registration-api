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
        self.clear_collection(entrypoint="form")
        self.insert_login_form()
        res = self.app.get("/form/", follow_redirects=True)
        form = res.json

    def test_get_property_form(self):
        self.clear_collection(entrypoint="properties")
        self.clear_collection(entrypoint="form")
        res = self.insert_property_form()

        self.assertEqual(res.status_code, 201)

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

        prop_user_res = self.insert(self.app, data=prop_user_data, entrypoint="/properties/")
        prop_pw_res = self.insert(self.app, data=prop_pw_data, entrypoint="/properties/")

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

    def insert_property_form(self):
        prop_label = {
            "label": "Label",
            "name": "label",
            "level": "administrative",
            "vocabulary_type": {"data_type": "text"},
            "description": "Human readable name"
        }

        prop_name = {
            "label": "Name",
            "name": "name",
            "level": "administrative",
            "vocabulary_type": {"data_type": "text"},
            "description": "Machine readable name"
        }

        prop_level = {
            "label": "Level",
            "name": "level",
            "level": "administrative",
            "vocabulary_type": {"data_type": "text"},
            "description": "Level of a property"
        }

        prop_synonyms = {
            "label": "Synonyms",
            "name": "synonyms",
            "level": "administrative",
            "vocabulary_type": {"data_type": "text"},
            "description": "The synonyms"
        }

        prop_description = {
            "label": "Description",
            "name": "description",
            "level": "administrative",
            "vocabulary_type": {"data_type": "text"},
            "description": "Description of a property"
        }

        prop_deprecated = {
            "label": "Deprecated",
            "name": "deprecated",
            "level": "administrative",
            "vocabulary_type": {"data_type": "boolean"},
            "description": "Status of a property"
        }

        prop_data_type = {
            "label": "Data Type",
            "name": "data_type",
            "level": "administrative",
            "vocabulary_type": {"data_type": "text"},
            "description": "The data type of a property"
        }

        prop_ctrl_voc = {
            "label": "Controlled Vocabulary",
            "name": "controlled_vocabulary",
            "level": "administrative",
            "vocabulary_type": {"data_type": "text"},
            "description": "Reference to a controlled vocabulary"
        }

        res_prop_label = self.insert(self.app, data=prop_label, entrypoint="/properties/")
        res_prop_name = self.insert(self.app, data=prop_name, entrypoint="/properties/")
        res_prop_level = self.insert(self.app, data=prop_level, entrypoint="/properties/")
        res_prop_synonyms = self.insert(self.app, data=prop_synonyms, entrypoint="/properties/")
        res_prop_description = self.insert(self.app, data=prop_description, entrypoint="/properties/")
        res_prop_deprecated = self.insert(self.app, data=prop_deprecated, entrypoint="/properties/")
        res_prop_data_type = self.insert(self.app, data=prop_data_type, entrypoint="/properties/")
        res_prop_ctrl_voc = self.insert(self.app, data=prop_ctrl_voc, entrypoint="/properties/")

        form_data = {
            "label": "Property",
            "name": "property",
            "description": "Form to change property",
            "fields": [
                {
                    "label": "Label",
                    "property": res_prop_label.json['id'],
                    "class_name": "StringField",
                },
                {
                    "label": "Name",
                    "property": res_prop_name.json["id"],
                    "class_name": "StringField",
                },
                {
                    "label": "Level",
                    "property": res_prop_level.json["id"],
                    "class_name": "SelectField",
                },
                {
                    "label": "Synonyms",
                    "property": res_prop_synonyms.json["id"],
                    "class_name": "StringField",
                    "kwargs": {"min_entries": 1},
                },
                {
                    "label": "",
                    "class_name": "FormField",
                    "name": "subform",
                    "fields": [
                        {
                            "label": "Data Type",
                            "class_name": "StringField",
                            "property": res_prop_data_type.json["id"]
                        },
                        {
                            "label": "Controlled Vocabulary",
                            "class_name": "StringField",
                            "property": res_prop_ctrl_voc.json["id"]
                        },
                    ]
                },
                {
                    "label": "Description",
                    "property": res_prop_description.json["id"],
                    "class_name": "TextAreaField",
                },
                {
                    "label": "Deprecated",
                    "property": res_prop_deprecated.json["id"],
                    "class_name": "BooleanField",
                },
            ],
        }

        return self.insert(self.app, data=form_data, entrypoint="/form/")

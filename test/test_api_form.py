from urllib.parse import urljoin
import requests
import unittest

from test import test_utils
from test.test_api_base import BaseTestCase

from dynamic_form.template_builder import PropertyTemplate, FormTemplate, FieldTemplate


# @unittest.skip
class MyTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(MyTestCase, cls).setUpClass()
        cls.route = "forms"
        cls.url = urljoin(cls.host, cls.route)

    def setUp(self) -> None:
        test_utils.clear_collections(self.url, ["ctrl_vocs", "properties", self.route])

    # ------------------------------------------------------------------------------------------------------------------
    # GET

    def test_retrieve_login_form(self):
        self.insert_login_form()
        res = requests.get(self.url)
        form = res.json()

    def test_get_property_form(self):
        res = self.insert_property_form()
        self.assertEqual(res.status_code, 201)

    # ------------------------------------------------------------------------------------------------------------------
    # POST

    def test_add_login_form(self):
        res = self.insert_login_form()

        self.assertEqual(res.status_code, 201)

    # ------------------------------------------------------------------------------------------------------------------
    # Helper methods

    def insert_login_form(self):

        props = [
            PropertyTemplate("Username", "username", "top", "Recognizable name"),
            PropertyTemplate("Password", "password", "top", "Secret to authenticate user")
        ]

        prop_url = urljoin(self.host, "properties")
        prop_map = self.insert_properties(prop_url, props)

        form_data = FormTemplate("Login", "login", "Form to login a user",)\
            .add_field(
            FieldTemplate("StringField", prop_map["username"],
                          validators={"args": {"objects": [
                              {"class_name": "DataRequired"},
                              {"class_name": "Length", "kwargs": {"max": 64, "min": 8}}
                          ]}}
            ))\

        return requests.post(url=self.url, json=form_data.to_dict())

    def insert_property_form(self):

        props = [
            PropertyTemplate("Label", "label", "administrative", "Human readable name"),
            PropertyTemplate("Name", "name", "administrative", "Machine readable name"),
            PropertyTemplate("Level", "level", "administrative", "Level of a property"),
            PropertyTemplate("Synonyms", "synonyms", "administrative", "The synonyms"),
            PropertyTemplate("Description", "description", "administrative", "Description of a property"),
            PropertyTemplate("Deprecated", "deprecated", "administrative", "Status of a property"),
            PropertyTemplate("Data Type", "data_type", "administrative", "The data type of a property"),
            PropertyTemplate("Controlled Vocabulary", "controlled_vocabulary",
                             "administrative", "Reference to a controlled vocabulary")
        ]

        prop_url = urljoin(self.host, "properties")
        prop_map = self.insert_properties(url=prop_url, props=props)

        # TODO: Replace with FormTemplate
        form_data = {
            "label": "Property",
            "name": "property",
            "description": "Form to change property",
            "fields": [
                {
                    "label": "Label",
                    "property": prop_map["label"],
                    "class_name": "StringField",
                },
                {
                    "label": "Name",
                    "property": prop_map["name"],
                    "class_name": "StringField",
                },
                {
                    "label": "Level",
                    "property": prop_map["level"],
                    "class_name": "SelectField",
                },
                {
                    "label": "Synonyms",
                    "property": prop_map["synonyms"],
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
                            "property": prop_map["data_type"]
                        },
                        {
                            "label": "Controlled Vocabulary",
                            "class_name": "StringField",
                            "property": prop_map["controlled_vocabulary"]
                        },
                    ]
                },
                {
                    "label": "Description",
                    "property": prop_map["description"],
                    "class_name": "TextAreaField",
                },
                {
                    "label": "Deprecated",
                    "property": prop_map["deprecated"],
                    "class_name": "BooleanField",
                },
            ],
        }

        return requests.post(url=self.url, json=form_data)

    @staticmethod
    def insert_properties(url, props):
        prop_map = {}

        for prop in props:
            res = requests.post(url=url, json=prop.to_dict())
            prop_map[prop.name] = res.json()["id"]

        return prop_map


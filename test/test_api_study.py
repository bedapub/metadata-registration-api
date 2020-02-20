from urllib.parse import urljoin
import requests
import unittest

from test.test_api_base import BaseTestCase
from test import test_utils

from dynamic_form.template_builder import PropertyTemplate, FormTemplate, FieldTemplate

# @unittest.skip
class StudyTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(StudyTestCase, cls).setUpClass()
        cls.route = "studies"
        cls.url = urljoin(cls.host, cls.route)

    def setUp(self) -> None:
        test_utils.clear_collections(entry_point=self.host, routes=["ctrl_vocs", "properties", "forms", self.route])

    def test_insert_generic_study(self):

        prop = self.insert_property()
        form = self.insert_form(prop)
        res = self.insert_study(prop)

        self.assertEqual(res.status_code, 201)
        self.assertTrue(all([key in res.json().keys() for key in ["message", "id"]]))

    def insert_property(self):

        props = [PropertyTemplate("Study Name", "study_name", "study", "The name of a study"),
                 PropertyTemplate("Study Description", "study_description", "study", "Detail of the study"),
                 PropertyTemplate("Platform", "platform", "study", "The used platform")
                 ]

        results = [requests.post(url=urljoin(self.host, "properties"), json=prop.to_dict()) for prop in props]

        prop_map = {prop.name: res.json()["id"] for prop, res in zip(props, results)}

        return prop_map

    def insert_form(self, prop):
        forms = [
            FormTemplate("Generic Study", "generic_study", "A generic study")\
                .add_field(
                FieldTemplate("StringField", prop["study_name"]))\
                .add_field(
                FieldTemplate("TextAreaField", prop["study_description"]))\
                .add_field(
                FieldTemplate("StringField", prop["platform"])
            )
        ]

        results = [requests.post(url=urljoin(self.host, "forms"), json=form.to_dict()) for form in forms]

        form_map = {prop.name: res.json()["id"] for prop, res in zip(forms, results)}

        return form_map

    def insert_study(self, prop):

        data = {
            "form_name": "generic_study",
            "initial_state": "generic_study",
            "entries": [
                {
                    "property": prop["study_name"],
                    "value": "A test study"
                },
                {
                    "property": prop["study_description"],
                    "value": "A study to test its behavior"
                },
                {
                    "property": prop["platform"],
                    "value": "expression"
                }
            ]
        }

        return requests.post(self.url, json=data)

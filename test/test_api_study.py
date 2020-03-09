import os
import unittest

import requests
from dynamic_form.errors import DataStoreException
from state_machine.errors import StateNotFoundException

from metadata_registration_api.errors import RequestBodyException, IdenticalPropertyException
from test.test_api_base import BaseTestCase
from scripts import setup, rna_seq_upload


class StudyExceptionTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(StudyExceptionTestCase, cls).setUpClass()

        cls.ctrl_voc_map, \
        cls.prop_map, \
        cls.form_map = setup.minimal_setup(cls.ctrl_voc_endpoint,
                                           cls.property_endpoint,
                                           cls.form_endpoint,
                                           cls.study_endpoint)

    def test_post_form_not_found_exception(self):

        study_data = {
            "form_name": "unknown",
            "initial_state": "",
            "entries": ""
        }

        res = requests.post(self.study_endpoint, json=study_data)
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.json()["error_type"], DataStoreException.__name__)

    def test_post_state_not_found_exception(self):
        study_data = {
            "form_name": "user_login",
            "initial_state": "unknown",
            "entries": ""
        }

        res = requests.post(self.study_endpoint, json=study_data)
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.json()["error_type"], StateNotFoundException.__name__)

    def test_post_validation_exception(self):

        for entries in ["unknown", list()]:

            study_data = {
                "form_name": "user_login",
                "initial_state": "BiokitUploadState",
                "entries": entries
            }

            res = requests.post(self.study_endpoint, json=study_data)
            self.assertEqual(res.status_code, 422)
            self.assertEqual(res.json()["error_type"], RequestBodyException.__name__)

    def test_post_identical_properties_exception(self):
        study_data = {
            "form_name": "user_login",
            "initial_state": "BiokitUploadState",
            "entries": [{"property": "Test 1"}, {"property": "Test 1"}]
        }

        res = requests.post(self.study_endpoint, json=study_data)
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.json()["error_type"], IdenticalPropertyException.__name__)


# @unittest.skip
class StudyTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(StudyTestCase, cls).setUpClass()
        cls.study_map = {}

    def setUp(self) -> None:
        self.ctrl_voc_map, self.prop_map, self.form_map = setup.minimal_setup(self.ctrl_voc_endpoint,
                                                                              self.property_endpoint,
                                                                              self.form_endpoint,
                                                                              self.study_endpoint)

        self.ctrl_voc_map.update(setup.add_study_related_ctrl_voc(self.host, self.credentials))
        self.prop_map.update(setup.add_study_related_properties(self.host, self.credentials, self.ctrl_voc_map))

    def test_upload_rna_seq_form(self):
        self.form_map.update(setup.add_rna_seq_form(self.host, self.credentials, self.prop_map))

        input_file = os.path.join(os.path.dirname(__file__), "ACpilot_mongodb.json")

        self.study_map.update(rna_seq_upload.post_study(input_file, host=self.host))

        # Ensure that inserted study is accessible
        study_endpoint = self.study_endpoint + f"/id/{self.study_map['ACpilot']}/"
        res = requests.get(study_endpoint)
        self.assertEqual(len(res.json()["entries"]), 10)

        res = requests.delete(study_endpoint)
        self.assertEqual(res.status_code, 200, f"Could not delete study with id {self.study_map['ACpilot']}")




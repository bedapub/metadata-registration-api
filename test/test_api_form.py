from urllib.parse import urljoin
import requests
import unittest

from test import test_utils
from test.test_api_base import BaseTestCase

from scripts import setup

# from dynamic_form.template_builder import PropertyTemplate, FormTemplate, FieldTemplate


# @unittest.skip
class MyTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(MyTestCase, cls).setUpClass()

    def setUp(self) -> None:
        self.ctrl_voc_map, \
        self.prop_map, \
        self.form_map = setup.minimal_setup(self.ctrl_voc_endpoint,
                                            self.property_endpoint,
                                            self.form_endpoint,
                                            self.study_endpoint)

    def test_get_individual_forms(self):
        for key, value in self.form_map.items():
            res = requests.get(self.form_endpoint + f"/id/{value}")

            self.assertEqual(res.status_code, 200, f"Fail to load form '{key}'")


    def test_get_all_forms(self):
        res = requests.get(self.form_endpoint)

        self.assertEqual(res.status_code, 200)

    # POST

    def test_insert_generic_study_form(self):
        self.ctrl_voc_map.update(setup.add_study_related_ctrl_voc(self.host, self.credentials))
        self.prop_map.update(setup.add_study_related_properties(self.host, self.credentials, self.ctrl_voc_map))
        self.form_map.update(setup.add_generic_study_form(self.host, self.credentials, self.prop_map))

    def test_insert_rna_seq_study_form(self):
        self.ctrl_voc_map.update(setup.add_study_related_ctrl_voc(self.host, self.credentials))
        self.prop_map.update(setup.add_study_related_properties(self.host, self.credentials, self.ctrl_voc_map))
        self.form_map.update(setup.add_rna_seq_form(self.host, self.credentials, self.prop_map))




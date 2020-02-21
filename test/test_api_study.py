from urllib.parse import urljoin
import requests
import unittest

from test.test_api_base import BaseTestCase


from scripts import setup, rna_seq_upload
from metadata_registration_api import my_utils

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
        self.study_map.update(rna_seq_upload.post_study("C:/Users/rafaelsm/PycharmProjects/ACpilot_mongodb.json",
                                                        host=self.host))

    def test_get_all_study(self):
        res = requests.get(self.study_endpoint)
        self.assertEqual(res.status_code, 200)



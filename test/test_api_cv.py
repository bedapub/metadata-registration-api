import unittest
from urllib.parse import urljoin
import requests

from test.test_api_base import BaseTestCase
from scripts import setup


# @unittest.skip
class TestCtrlVocStatic(BaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(TestCtrlVocStatic, cls).setUpClass()
        cls.route = "ctrl_voc"
        cls.url = urljoin(cls.host, cls.route)

        cls.ctrl_voc_map, \
        cls.prop_map, \
        cls.form_map = setup.minimal_setup(cls.ctrl_voc_endpoint,
                                           cls.property_endpoint,
                                           cls.form_endpoint,
                                           cls.study_endpoint)

    # ------------------------------------------------------------------------------------------------------------------
    # GET

    def test_get_individual_ctrl_voc(self):
        for key, value in self.ctrl_voc_map.items():
            res = requests.get(url=self.ctrl_voc_endpoint + f"/id/{value}")

            self.assertEqual(res.status_code, 200, f"Fail to load ctrl voc '{key}'")

    def test_get_all_ctrl_voc(self):
        for deprecated in [True, False]:
            res = requests.get(url=self.ctrl_voc_endpoint, params={"deprecated": deprecated})
            self.assertEqual(res.status_code, 200, f"Fail deprecated : {deprecated}")


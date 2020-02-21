import unittest
from urllib.parse import urljoin
import requests

from test.test_api_base import BaseTestCase
from test import test_utils
from scripts import setup


# @unittest.skip
class TestCtrlVoc(BaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(TestCtrlVoc, cls).setUpClass()
        cls.route = "ctrl_voc"
        cls.url = urljoin(cls.host, cls.route)

    def setUp(self) -> None:
        self.ctrl_voc_map, \
        self.prop_map, \
        self.form_map = setup.minimal_setup(self.ctrl_voc_endpoint,
                                            self.property_endpoint,
                                            self.form_endpoint,
                                            self.study_endpoint)

    # ------------------------------------------------------------------------------------------------------------------
    # GET

    def test_get_individual_ctrl_voc(self):
        for key, value in self.ctrl_voc_map.items():
            res = requests.get(url=self.ctrl_voc_endpoint + f"/id/{value}")

            self.assertEqual(res.status_code, 200, f"Fail to load ctrl voc '{key}'")

    def test_get_all_ctrl_voc(self):
        res = requests.get(url=self.ctrl_voc_endpoint)

        self.assertEqual(res.status_code, 200)

    # ------------------------------------------------------------------------------------------------------------------
    # PUT

#    def test_add_second_item_to_cv(self):
#        """"""
#
#        data = {"label": "Test CV",
#                "name": "Test CV",
#                "description": "Test CV",
#                "items": [{"label": "Test item 1",
#                           "name": "Test item 1",
#                           "description": "Simple description",
#                           "synonyms": ["A test", "This is a test label"]
#                           }]
#                }
#
#        res = requests.post(url=self.url, json=data)
#
#        self.assertEqual(res.status_code, 201)
#        self.assertTrue(all([key in res.json().keys() for key in ["message", "id"]]))
#
#        entry_id = res.json()["id"]
#
#        data = {"label": "Test CV",
#                "name": "Test CV",
#                "description": "Test CV",
#                "items": [
#                    {
#                        "label": "Test item 1",
#                        "name": "Test item 1",
#                        "description": "Simple description",
#                        "synonyms": ["A test", "This is a test label"]
#                    },
#                    {
#                        "label": "Test item 2",
#                        "name": "Test item 2",
#                        "description": "Simple description",
#                        "synonyms": ["A test", "This is a test label"]
#                    }
#                ]
#                }
#
#        url = urljoin(self.host, self.route + f"/id/{entry_id}")
#
#        res = requests.put(url=url, json=data)
#
#        self.assertEqual(res.status_code, 200)
#
#        res = requests.get(url=url)
#
#        self.assertEqual(res.status_code, 200)
#        self.assertEqual(len(res.json()['items']), 2)
#
#    # ------------------------------------------------------------------------------------------------------------------
#    # DELETE
#
#    def test_deprecate_single_entry(self):
#        res = self.insert_minimal_cv()
#
#        url = urljoin(self.host, self.route + f"/id/{res.json()['id']}")
#
#        res = requests.delete(url=url)
#
#        res = requests.get(url=url, params={"deprecated": True})
#
#        self.assertTrue(res.json()["deprecated"])
#
#    def test_delete_all(self):
#
#        for complete in [True, False]:
#            test_utils.clear_collections(entry_point=self.host, routes=[self.route])
#            self.insert_two()
#
#            res = requests.delete(url=self.url, params={"complete": complete})
#
#            res_delete = requests.get(url=self.url, params={"deprecated": True})
#
#            if complete:
#                self.assertEqual(len(res_delete.json()), 0)
#            else:
#                self.assertEqual(len(res_delete.json()), 2)
#
#            res = requests.get(url=self.url, params={"deprecated": False})
#            self.assertEqual(len(res.json()), 0)
#
#    # ------------------------------------------------------------------------------------------------------------------
#    # Helper methods
#
#    def insert_minimal_cv(self):
#        data = {"label": "Test CV",
#                "name": "Test CV",
#                "description": "Test CV",
#                "items": [{"label": "Test item 1", "name": "Test item 1"}]}
#
#        return requests.post(url=self.url, json=data)
#
#    def insert_full_cv(self):
#        data = {"label": "Test CV",
#                "name": "Test CV",
#                "description": "Test CV",
#                "items": [{"label": "Test item 1",
#                           "name": "Test item 1",
#                           "description": "Simple description",
#                           "synonyms": ["A test", "This is a test label"]
#                           }]
#                }
#
#        return requests.post(url=self.url, json=data)
#
#    def insert_two(self):
#        data1 = {"label": "Test CV 1",
#                 "name": "Test CV 1",
#                 "description": "Test CV 1",
#                 "items": [{"label": "Test item 1", "name": "Test item 1"}],
#                 "deprecated": False}
#
#        data2 = {"label": "Test CV 2",
#                 "name": "Test CV 2",
#                 "description": "Test CV 2",
#                 "items": [{"label": "Test item 1", "name": "Test item 1"}],
#                 "deprecated": True}
#
#        for data in [data1, data2]:
#            requests.post(url=self.url, json=data)
#
#if __name__ == '__main__':
#    unittest.main()

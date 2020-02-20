import unittest
from urllib.parse import urljoin
import requests

from test.test_api_base import BaseTestCase
from test import test_utils


# @unittest.skip
class MyTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(MyTestCase, cls).setUpClass()
        cls.route = "ctrl_vocs"
        cls.url = urljoin(cls.host, cls.route)

    def setUp(self) -> None:
        test_utils.clear_collections(entry_point=self.host, routes=[self.route, "properties"])


    # ------------------------------------------------------------------------------------------------------------------
    # GET

    def test_get_property_no_param(self):
        """ Get list of properties without query parameter"""
        self.insert_two()

        res = requests.get(url=self.url)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)

    def test_get_cv_deprecate_param(self):
        """ Get list of properties with query parameter deprecate """
        self.insert_two()

        for deprecated in [True, False]:
            res = requests.get(url=f"{self.url}?deprecated={deprecated}")

            self.assertEqual(res.status_code, 200)
            if deprecated:
                self.assertEqual(len(res.json()), 2)
            else:
                self.assertEqual(len(res.json()), 1)

    # ------------------------------------------------------------------------------------------------------------------
    # POST

    def test_insert_cv_minimal(self):
        """ Add minimal controlled vocabulary """

        res = self.insert_minimal_cv()

        self.assertEqual(res.status_code, 201)
        self.assertTrue(all([key in res.json().keys() for key in ["message", "id"]]))

    def test_insert_cv_full(self):
        """ Add a controlled vocabulary containing a description and a synonyms """

        res = self.insert_full_cv()

        self.assertEqual(res.status_code, 201)
        self.assertTrue(all([key in res.json().keys() for key in ["message", "id"]]))

    # ------------------------------------------------------------------------------------------------------------------
    # PUT

    def test_add_second_item_to_cv(self):
        """"""

        data = {"label": "Test CV",
                "name": "Test CV",
                "description": "Test CV",
                "items": [{"label": "Test item 1",
                           "name": "Test item 1",
                           "description": "Simple description",
                           "synonyms": ["A test", "This is a test label"]
                           }]
                }

        res = requests.post(url=self.url, json=data)

        self.assertEqual(res.status_code, 201)
        self.assertTrue(all([key in res.json().keys() for key in ["message", "id"]]))

        entry_id = res.json()["id"]

        data = {"label": "Test CV",
                "name": "Test CV",
                "description": "Test CV",
                "items": [
                    {
                        "label": "Test item 1",
                        "name": "Test item 1",
                        "description": "Simple description",
                        "synonyms": ["A test", "This is a test label"]
                    },
                    {
                        "label": "Test item 2",
                        "name": "Test item 2",
                        "description": "Simple description",
                        "synonyms": ["A test", "This is a test label"]
                    }
                ]
                }

        url = urljoin(self.host, self.route + f"/id/{entry_id}")

        res = requests.put(url=url, json=data)

        self.assertEqual(res.status_code, 200)

        res = requests.get(url=url)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()['items']), 2)

    # ------------------------------------------------------------------------------------------------------------------
    # DELETE

    def test_deprecate_single_entry(self):
        res = self.insert_minimal_cv()

        url = urljoin(self.host, self.route + f"/id/{res.json()['id']}")

        res = requests.delete(url=url)

        res = requests.get(url=url, params={"deprecated": True})

        self.assertTrue(res.json()["deprecated"])

    def test_delete_all(self):

        for complete in [True, False]:
            test_utils.clear_collections(entry_point=self.host, routes=[self.route])
            self.insert_two()

            res = requests.delete(url=self.url, params={"complete": complete})

            res_delete = requests.get(url=self.url, params={"deprecated": True})

            if complete:
                self.assertEqual(len(res_delete.json()), 0)
            else:
                self.assertEqual(len(res_delete.json()), 2)

            res = requests.get(url=self.url, params={"deprecated": False})
            self.assertEqual(len(res.json()), 0)

    # ------------------------------------------------------------------------------------------------------------------
    # Helper methods

    def insert_minimal_cv(self):
        data = {"label": "Test CV",
                "name": "Test CV",
                "description": "Test CV",
                "items": [{"label": "Test item 1", "name": "Test item 1"}]}

        return requests.post(url=self.url, json=data)

    def insert_full_cv(self):
        data = {"label": "Test CV",
                "name": "Test CV",
                "description": "Test CV",
                "items": [{"label": "Test item 1",
                           "name": "Test item 1",
                           "description": "Simple description",
                           "synonyms": ["A test", "This is a test label"]
                           }]
                }

        return requests.post(url=self.url, json=data)

    def insert_two(self):
        data1 = {"label": "Test CV 1",
                 "name": "Test CV 1",
                 "description": "Test CV 1",
                 "items": [{"label": "Test item 1", "name": "Test item 1"}],
                 "deprecated": False}

        data2 = {"label": "Test CV 2",
                 "name": "Test CV 2",
                 "description": "Test CV 2",
                 "items": [{"label": "Test item 1", "name": "Test item 1"}],
                 "deprecated": True}

        for data in [data1, data2]:
            requests.post(url=self.url, json=data)

if __name__ == '__main__':
    unittest.main()

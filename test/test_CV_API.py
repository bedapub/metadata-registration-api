import unittest

from api_service.app import create_app
from test.test_Base_API import AbstractTest


class MyTestCase(unittest.TestCase, AbstractTest):

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app(config="TESTING").test_client()
        AbstractTest.clear_collection(cls.app)

    def setUp(self) -> None:
        MyTestCase.clear_collection(MyTestCase.app)
        MyTestCase.clear_collection(MyTestCase.app, entrypoint="/ctrl_voc")


    # ------------------------------------------------------------------------------------------------------------------
    # GET

    def test_get_property_no_param(self):
        """ Get list of properties without query parameter"""
        MyTestCase.insert_two(self.app)

        res = self.app.get("/ctrl_voc", follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json), 1)

    def test_get_cv_deprecate_param(self):
        """ Get list of properties with query parameter deprecate """
        MyTestCase.insert_two(self.app)

        for deprecate in [True, False]:
            res = self.app.get(f"/ctrl_voc?deprecate={deprecate}", follow_redirects=True)

            self.assertEqual(res.status_code, 200)
            if deprecate:
                self.assertEqual(len(res.json), 2)
            else:
                self.assertEqual(len(res.json), 1)

    # ------------------------------------------------------------------------------------------------------------------
    # POST

    def test_insert_cv_minimal(self):
        """ Add minimal controlled vocabulary """

        data = {"label": "Test CV",
                "name": "Test CV",
                "description": "Test CV",
                "items": [{"label": "Test item 1", "name": "Test item 1"}]}

        res = AbstractTest.insert(MyTestCase.app, data, entrypoint="/ctrl_voc")

        self.assertEqual(res.status_code, 201)
        self.assertTrue(all([key in res.json.keys() for key in ["message", "id"]]))

    def test_insert_cv_full(self):
        """ Add a controlled vocabulary containing a description and a synonyms """

        data = {"label": "Test CV",
                "name": "Test CV",
                "description": "Test CV",
                "items": [{"label": "Test item 1",
                           "name": "Test item 1",
                           "description": "Simple description",
                           "synonyms": ["A test", "This is a test label"]
                           }]
                }

        res = AbstractTest.insert(MyTestCase.app, data, entrypoint="/ctrl_voc")

        self.assertEqual(res.status_code, 201)
        self.assertTrue(all([key in res.json.keys() for key in ["message", "id"]]))

    # ------------------------------------------------------------------------------------------------------------------
    # Helper methods

    @staticmethod
    def insert_two(app):
        data1 = {"label": "Test CV 1",
                 "name": "Test CV 1",
                 "description": "Test CV 1",
                 "items": [{"label": "Test item 1", "name": "Test item 1"}],
                 "deprecate": False}

        data2 = {"label": "Test CV 2",
                 "name": "Test CV 2",
                 "description": "Test CV 2",
                 "items": [{"label": "Test item 1", "name": "Test item 1"}],
                 "deprecate": True}

        for data in [data1, data2]:
            AbstractTest.insert(MyTestCase.app, data=data, entrypoint="/ctrl_voc")

if __name__ == '__main__':
    unittest.main()

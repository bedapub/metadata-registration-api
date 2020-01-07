import unittest

from mongoengine.errors import NotUniqueError

from test.test_api_base import AbstractTest
from api_service.app import create_app


class MyTestCase(unittest.TestCase, AbstractTest):

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app(config="TESTING").test_client()
        cls.clear_collection()

    def setUp(self) -> None:
        MyTestCase.clear_collection()
        MyTestCase.clear_collection(entrypoint="/ctrl_vocs/")

    # ------------------------------------------------------------------------------------------------------------------
    # GET

    def test_get_property_no_param(self):
        """ Get list of properties without query parameter"""
        MyTestCase.insert_two(self.app)

        res = self.app.get("/properties/", follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json), 1)

    def test_get_property_deprecate_param(self):
        """ Get list of properties with query parameter deprecate """
        MyTestCase.insert_two(self.app)

        for deprecated in [True, False]:
            res = self.app.get(f"/properties?deprecated={deprecated}", follow_redirects=True)

            self.assertEqual(res.status_code, 200)
            if deprecated:
                self.assertEqual(len(res.json), 2)
            else:
                self.assertEqual(len(res.json), 1)

    def test_get_property_singe(self):
        """ Get single property by id """
        results = MyTestCase.insert_two(self.app)

        entrypoint = "/properties/"
        res = self.app.get(f"{entrypoint}id/{results[0].json['id']}", follow_redirects=True)

        self.assertEqual(res.status_code, 200)

    # ------------------------------------------------------------------------------------------------------------------
    # PUT

    def test_append_to_synonyms_entire_dataset(self):
        """ Update by passing the entire dataset to the API"""

        data = {"label": "First Name",
                "name": "firstname",
                "level": "administrative",
                "vocabulary_type": {"data_type": "text"},
                "synonyms": ["forename"],
                "description": "The first name of a person",
                "deprecated": False
                }

        res = self.insert(MyTestCase.app, data, check_status=False)
        self.assertEqual(res.status_code, 201)

        entry_id = res.json["id"]
        data.update({"synonyms": ["forename", "given name"]})

        res = MyTestCase.app.put(f"/properties/id/{entry_id}", json=data, follow_redirects=True)

        self.assertEqual(res.status_code, 200)

        res = MyTestCase.get(MyTestCase.app, entrypoint=f"/properties/id/{entry_id}")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json["synonyms"], ["forename", "given name"])

    def test_append_to_synonyms_partial(self):
        """ Updating by just passing the key-value pair which changed"""

        data = {"label": "First Name",
                "name": "firstname",
                "level": "administrative",
                "vocabulary_type": {"data_type": "text"},
                "synonyms": ["forename"],
                "description": "The first name of a person",
                "deprecated": False
                }

        res = self.insert(MyTestCase.app, data, check_status=False)
        self.assertEqual(res.status_code, 201)

        entry_id = res.json["id"]
        update = {"synonyms": ["forename", "given name"]}

        res = MyTestCase.app.put(f"/properties/id/{entry_id}", json=update, follow_redirects=True)

        self.assertEqual(res.status_code, 200)

        res = MyTestCase.get(MyTestCase.app, entrypoint=f"/properties/id/{entry_id}")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json["synonyms"], ["forename", "given name"])

    # ------------------------------------------------------------------------------------------------------------------
    # POST

    def test_post_property(self):
        """ Insert a minimal property (w/o controlled vocabulary) """

        data = {"label": "Test",
                "name": "Test",
                "level": "TEST",
                "description": "Simple description"}

        res = MyTestCase.insert(MyTestCase.app, data)
        self.assertEqual(res.status_code, 201, f"Could not create entry: {res.json}")

    def test_post_property_wrong_format(self):
        """ Try to insert a property in the wrong format """

        data = {"label": "Test",
                # "name": "Test", # name is required
                "level": "TEST",
                "description": "Simple description"
                }

        res = MyTestCase.insert(MyTestCase.app, data, check_status=False)
        self.assertEqual(res.status_code, 400)
        self.assertTrue("Validation error:" in res.json["message"])

    def test_post_property_cv(self):
        """ Insert property with vocabulary other than cv"""

        data = {"label": "string",
                "name": "string",
                "level": "string",
                "vocabulary_type": {"data_type": "text"},
                "synonyms": ["string", ],
                "description": "string",
                "deprecated": False
                }

        res = self.insert(MyTestCase.app, data, check_status=False)

        self.assertEqual(res.status_code, 201)

    def test_post_property_cv_error(self):
        """ Insert property with vocabulary other than cv"""

        data = {"label": "string",
                "name": "string",
                "level": "string",
                "vocabulary_type": {"data_type": "text", "controlled_vocabulary": "String"},
                "synonyms": ["string", ],
                "description": "string",
                "deprecated": False
                }

        res = self.insert(MyTestCase.app, data, check_status=False)

        self.assertEqual(res.status_code, 201)

    def test_post_property_cv_reference(self):
        """ Insert property with correct cv """

        cv = {"label": "Test CV",
              "name": "Test CV",
              "description": "Test CV",
              "items": [
                  {"label": "test 1", "name": "test 1"}, {"label": "test 2", "name": "test 2"}
              ]
              }

        MyTestCase.insert(MyTestCase.app, data=cv, entrypoint="/ctrl_vocs/")

        id = MyTestCase.get_ids(MyTestCase.app, entrypoint="/ctrl_vocs/").json[0]['id']

        data = {"label": "string",
                "name": "string",
                "level": "string",
                "vocabulary_type": {"data_type": "cv", "controlled_vocabulary": id},
                "synonyms": ["string", ],
                "description": "string",
                "deprecated": False
                }

        res = self.insert(MyTestCase.app, data)

        self.assertEqual(res.status_code, 201)

    def test_post_property_double_entry(self):
        """ Try to insert properties twice """
        results_1 = MyTestCase.insert_two(MyTestCase.app)
        for res in results_1:
            self.assertEqual(res.status_code, 201)

        results_2 = MyTestCase.insert_two(MyTestCase.app, check_status=False)

        for res in results_2:
            self.assertEqual(res.status_code, 409)
            self.assertTrue("The entry already exists." in res.json['message'])

    def test_post_property_cv_not_id_error(self):
        """ Insert property with id in wrong format"""

        data = {"label": "string",
                "name": "string",
                "level": "string",
                "vocabulary_type": {"data_type": "cv", "controlled_vocabulary": "abc"},
                "synonyms": ["string", ],
                "description": "string",
                "deprecated": False
                }

        res = self.insert(MyTestCase.app, data, check_status=False)

        self.assertEqual(res.status_code, 404)
        self.assertTrue("Trying to dereference unknown document DBRef" in res.json['message'])

    def test_post_property_cv_not_found_error(self):
        """" Insert property with invalid id (does not exist)"""

        data = {"label": "string",
                "name": "string",
                "level": "string",
                "vocabulary_type": {"data_type": "cv", "controlled_vocabulary": "5b6bf449acf15441d0f87b4f"},
                "synonyms": ["string", ],
                "description": "string",
                "deprecated": False
                }

        res = self.insert(MyTestCase.app, data, check_status=False)

        self.assertEqual(res.status_code, 404)
        self.assertTrue("Trying to dereference unknown document DBRef" in res.json['message'])

    # ------------------------------------------------------------------------------------------------------------------
    # Delete

    def test_delete_individual_no_param(self):
        MyTestCase.clear_collection()
        MyTestCase.insert_two(self.app)

        res = MyTestCase.get_ids(MyTestCase.app)

        for entry in res.json:
            res = self.app.delete(f"/properties/id/{entry['id']}", follow_redirects=True)

        res_deprecate = self.app.get("/properties?deprecated=True", follow_redirects=True)
        res = self.app.get("/properties?deprecated=False", follow_redirects=True)

        self.assertEqual(len(res_deprecate.json), 2)
        self.assertEqual(len(res.json), 0)

    def test_delete_individual_complete_param(self):
        for complete in [True, False]:
            MyTestCase.clear_collection()
            MyTestCase.insert_two(self.app)

            # Get all entries (also the deprecated) to delete the completely
            res = MyTestCase.get_ids(MyTestCase.app, deprecated=complete)

            for entry in res.json:
                self.app.delete(f"/properties/id/{entry['id']}?complete={complete}", follow_redirects=True)

            res_deprecate = self.app.get("/properties?deprecated=True", follow_redirects=True)
            if complete:
                self.assertEqual(len(res_deprecate.json), 0)
            else:
                self.assertEqual(len(res_deprecate.json), 2)

            res = self.app.get("/properties?deprecated=False", follow_redirects=True)
            self.assertEqual(len(res.json), 0)

    def test_delete(self):
        for complete in [True, False]:
            MyTestCase.clear_collection()
            MyTestCase.insert_two(self.app)

            res = self.app.delete(f"/properties?complete={complete}", follow_redirects=True)

            res_delete = self.app.get("/properties?deprecated=True", follow_redirects=True)
            if complete:
                self.assertEqual(len(res_delete.json), 0)
            else:
                self.assertEqual(len(res_delete.json), 2)

        res = self.app.get("/properties?deprecated=False", follow_redirects=True)
        self.assertEqual(len(res.json), 0)

    # ------------------------------------------------------------------------------------------------------------------
    # Helper methods

    @staticmethod
    def insert_two(app, check_status=True):
        """ Insert a normal and a deprecated entry"""

        data1 = {"label": "label1",
                 "name": "name1",
                 "level": "level_1",
                 "description": "description 1",
                 "deprecated": False}

        data2 = {"label": "label2",
                 "name": "name2",
                 "level": "level_2",
                 "description": "description 2",
                 "deprecated": True}

        res = []
        for data in [data1, data2]:
            res.append(MyTestCase.insert(MyTestCase.app, data, check_status=check_status))

        return res


if __name__ == '__main__':
    unittest.main()

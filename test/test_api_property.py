import requests
import unittest

from scripts import setup
from test_api_base import BaseTestCase

from dynamic_form.template_builder import \
    ControlledVocabularyTemplate,\
    ValueTypeTemplate, \
    ItemTemplate, \
    PropertyTemplate


# @unittest.skip
class PropertyGetTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(PropertyGetTestCase, cls).setUpClass()
        cls.url = cls.property_endpoint

        setup.clear_collection(cls.ctrl_voc_endpoint)
        setup.clear_collection(cls.property_endpoint)
        cls.results = insert_two(cls)

    # ------------------------------------------------------------------------------------------------------------------
    # GET

    def test_get_property_no_param(self):
        """ Get list of properties without query parameter"""
        res = requests.get(url=self.url)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)

    def test_get_property_deprecate_param(self):
        """ Get list of properties with query parameter deprecate """
        for deprecated in [True, False]:
            res = requests.get(url=self.url, params={"deprecated": deprecated})

            self.assertEqual(res.status_code, 200)
            if deprecated:
                self.assertEqual(len(res.json()), 2)
            else:
                self.assertEqual(len(res.json()), 1)

    def test_get_property_single(self):
        """ Get single property by id """
        url = self.url + f"/id/{self.results[0].json()['id']}"
        res = requests.get(url=url)

        self.assertEqual(res.status_code, 200)


class PropertyTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(PropertyTestCase, cls).setUpClass()
        cls.url = cls.property_endpoint

    def setUp(self) -> None:
        setup.clear_collection(self.ctrl_voc_endpoint)
        setup.clear_collection(self.property_endpoint)

    def test_append_to_synonyms_entire_dataset(self):
        """ Update by passing the entire dataset to the API"""

        data = PropertyTemplate(
            "First Name", "firstname", "administrative","The first name of a person", synonyms=["forename"]
        )

        res = requests.post(url=self.url, json=data.to_dict())
        self.assertEqual(res.status_code, 201)

        # Update the entry
        data.synonyms = ["forename", "given name"]

        entry_id = res.json()["id"]
        url_id = self.url + f"/id/{entry_id}"

        res = requests.put(url=url_id, json=data.to_dict())
        self.assertEqual(res.status_code, 200)

        res = requests.get(url=url_id)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["synonyms"], ["forename", "given name"])

    def test_append_to_synonyms_partial(self):
        """ Updating by just passing the key-value pair which changed"""

        data = PropertyTemplate(
            "First Name", "firstname", "administrative","The first name of a person", synonyms=["forename"]
        )

        res = requests.post(url=self.url, json=data.to_dict())
        self.assertEqual(res.status_code, 201)

        # Only change the attribute
        update = {"synonyms": ["forename", "given name"]}

        entry_id = res.json()["id"]
        url_id = self.url + f"/id/{entry_id}"

        res = requests.put(url=url_id, json=update)
        self.assertEqual(res.status_code, 200)

        res = requests.get(url=url_id)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["synonyms"], ["forename", "given name"])

    # ------------------------------------------------------------------------------------------------------------------
    # POST

    def test_post_property_cv(self):
        """ Insert property with vocabulary other than cv"""

        data = PropertyTemplate("string", "string", "string",  "string")

        res = requests.post(url=self.url, json=data.to_dict())
        self.assertEqual(res.status_code, 201)

    @unittest.skip
    def test_post_property_cv_error(self):
        """ Insert property with vocabulary other than cv"""

        data = {"label": "string",
                "name": "string",
                "level": "string",
                "value_type": {"data_type": "text", "controlled_vocabulary": "String"},
                "synonyms": ["string", ],
                "description": "string",
                "deprecated": False
                }

        res = self.insert(data, check_status=False)

        self.assertEqual(res.status_code, 201)

    def test_post_property_cv_reference(self):
        """ Insert property with correct cv """

        data = PropertyTemplate("string", "string", "string", "string",
                                ValueTypeTemplate("ctrl_voc",
                                                  ControlledVocabularyTemplate("Test CV", "Test CV", "Test CV")
                                                  .add_item(ItemTemplate("test 1", "test 1", "First item"))
                                                  .add_item(ItemTemplate("test 2", "test 2", "First item"))))

        res = requests.post(url=self.url, json=data.to_dict())
        self.assertEqual(res.status_code, 201)

    def test_post_property_double_entry(self):
        """ Try to insert properties twice """
        insert_two(self)

        with self.assertRaises(Exception):
            results_2 = insert_two(self)

            for res in results_2:
                self.assertEqual(res.status_code, 409)
                self.assertTrue("The entry already exists." in res.json()['message'])

    # def test_post_property_cv_not_id_error(self):
    #     """ Insert property with id in wrong format"""
    #
    #     data = PropertyTemplate("string", "string", "string", "description": "string","value_type": {"data_type": "ctrl_voc",
    #                                                                          "controlled_vocabulary": "abc"},
    #
    #             "deprecated": False
    #             }
    #
    #     res = self.insert(data, check_status=False)
    #
    #     self.assertEqual(res.status_code, 404)
    #     self.assertTrue("Trying to dereference unknown document DBRef" in res.json['message'])

    # def test_post_property_cv_not_found_error(self):
    #     """" Insert property with invalid id (does not exist)"""
    #
    #     data = {"label": "string",
    #             "name": "string",
    #             "level": "string",
    #             "value_type": {"data_type": "ctrl_voc", "controlled_vocabulary": "5b6bf449acf15441d0f87b4f"},
    #             "synonyms": ["string", ],
    #             "description": "string",
    #             "deprecated": False
    #             }
    #
    #     res = self.insert(data, check_status=False)
    #
    #     self.assertEqual(res.status_code, 404)
    #     self.assertTrue("Trying to dereference unknown document DBRef" in res.json['message'])

    # ------------------------------------------------------------------------------------------------------------------
    # Delete

    def test_delete_individual_no_param(self):
        results = insert_two(self)

        for res in results:
            res = requests.delete(url=self.url + f"/id/{res.json()['id']}")
            self.assertEqual(res.status_code, 200)

        res_deprecate = requests.get(url=self.url, params={"deprecated": True})
        res = requests.get(url=self.url, params={"deprecated": False})

        self.assertEqual(len(res_deprecate.json()), 2)
        self.assertEqual(len(res.json()), 0)

    def test_delete_individual_complete_param(self):
        for complete in [True, False]:
            setup.clear_collection(self.ctrl_voc_endpoint)
            setup.clear_collection(self.property_endpoint)
            results = insert_two(self)

            for i, res in enumerate(results):
                res_delete = requests.delete(url=self.url + f"/id/{res.json()['id']}", params={"complete": complete})
                if res_delete.status_code != 200:
                    raise Exception(f"Deletion of {results[i].json()['id']} was not successful. "
                                    f"{res_delete.json()['id']}")

            res_deprecate = requests.get(url=self.url, params={"deprecated": True})

            if complete:
                self.assertEqual(len(res_deprecate.json()), 0)
            else:
                self.assertEqual(len(res_deprecate.json()), 2)

            res = requests.get(url=self.url, params={"deprecated": False})
            self.assertEqual(len(res.json()), 0)

    def test_delete(self):
        for complete in [True, False]:
            setup.clear_collection(self.ctrl_voc_endpoint)
            setup.clear_collection(self.property_endpoint)
            insert_two(self)

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


def insert_two(self):
    """ Insert a normal and a deprecated entry"""

    props = [
        PropertyTemplate("label1", "name1", "level_1", "description 1"),
        PropertyTemplate("label2", "name2", "level_2", "description 2", deprecated=True),
    ]

    results = [requests.post(self.url, json=prop.to_dict()) for prop in props]

    for index, res in enumerate(results):
        if res.status_code != 201:
            raise Exception(f"Could not insert {props[index]}. {res.json()}")

    return results



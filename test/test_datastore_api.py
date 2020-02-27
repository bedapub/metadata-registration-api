import unittest
import time

from test.test_api_base import BaseTestCase

from scripts import setup
from metadata_registration_api.datastore_api import ApiDataStore


from dynamic_form import FormManager
from dynamic_form.errors import DataStoreException


class MyTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(MyTestCase, cls).setUpClass()
        time.sleep(0.2)
        cls.data_store = ApiDataStore(url=cls.form_endpoint)

    def setUp(self) -> None:
        self.ctrl_voc_map, \
        self.prop_map, \
        self.form_map = setup.minimal_setup(self.ctrl_voc_endpoint,
                                            self.property_endpoint,
                                            self.form_endpoint,
                                            self.study_endpoint)

    def test_load_form(self):
        form_tempaltes = self.data_store.load_forms()

    def test_load_form_by_id(self):
        form_template = self.data_store.load_form(self.form_map["user_login"])
        self.assertEqual(len(form_template), 6)

    def test_load_form_by_wrong_id(self):
        with self.assertRaises(DataStoreException):
            form_template = self.data_store.load_form("123")
            next(form_template)

    def test_load_form_by_name(self):
        form_template = self.data_store.load_form_by_name("user_login")
        self.assertEqual(len(form_template), 6)

    def test_load_form_by_wrong_name(self):
        with self.assertRaises(DataStoreException):
            self.data_store.load_form_by_name("unknown")

    def test_deprecate_form(self):
        res = self.data_store.deprecate_form(self.form_map["user_login"])
        self.assertEqual(len(res), 1)



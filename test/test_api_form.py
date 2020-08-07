import requests

from test_api_base import BaseTestCase

from scripts import setup


class FormReadTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(FormReadTestCase, cls).setUpClass()

        cls.ctrl_voc_map, \
        cls.prop_map, \
        cls.form_map = setup.minimal_setup(cls.ctrl_voc_endpoint,
                                           cls.property_endpoint,
                                           cls.form_endpoint,
                                           cls.study_endpoint)

    @classmethod
    def tearDownClass(cls) -> None:
        super(FormReadTestCase, cls).tearDownClass()

    def test_get_individual_forms(self):
        for key, value in self.form_map.items():
            res = requests.get(self.form_endpoint + f"/id/{value}")

            self.assertEqual(res.status_code, 200, f"Fail to load form '{key}'")

    def test_get_all_forms(self):
        res = requests.get(self.form_endpoint)

        self.assertEqual(res.status_code, 200)


class FormInsertTestCase(BaseTestCase):

    def setUp(self) -> None:
        self.ctrl_voc_map, \
        self.prop_map, \
        self.form_map = setup.minimal_setup(self.ctrl_voc_endpoint,
                                            self.property_endpoint,
                                            self.form_endpoint,
                                            self.study_endpoint)

        self.ctrl_voc_map.update(setup.add_study_related_ctrl_voc(self.ctrl_voc_endpoint))
        self.prop_map.update(setup.add_study_related_properties(self.property_endpoint,
                                                                self.ctrl_voc_map))

    def test_insert_generic_study_form(self):
        self.form_map.update(setup.add_generic_study_form(self.form_endpoint,
                                                          self.prop_map))

    def test_insert_rna_seq_study_form(self):
        self.form_map.update(setup.add_rna_seq_form(self.form_endpoint,
                                                    self.prop_map))




import unittest

from metadata_registration_api.api import api_utils


class TestAPI_Util(unittest.TestCase):

    def test_meta_information_empty_change_log(self):

        state = "Initial test state"

        m = api_utils.MetaInformation(state=state)

        actual_json = m.to_json()
        expected_json = {"state": state, "change_log": []}

        self.assertEqual(expected_json, actual_json)

    def test_study_entry_form_format(self):
        mapper = {"1": "fields", "2": "datafile", "3": "path", "4": "method", "5": "name", "6": "datafiles"}

        entities = [
            {"prop": "5", "value": "test name"},
            {"prop": "6",
                "value": [
                    {"prop": "2", "value": [{"prop": "3", "value": "/pstore/"}, {"prop": "4", "value": "count"}]},
                    {"prop": "2", "value": [{"prop": "3", "value": "/pstore/"}, {"prop": "4", "value": "count"}]},
                ]
             }
        ]

        actual = api_utils.json_input_to_form_format(entities, mapper, key_name="prop", value_name="value")

        expected = {
            "name": "test name", "datafiles":
                [
                    {"datafile": {"path": "/pstore/", "method": "count"}},
                    {"datafile": {"path": "/pstore/", "method": "count"}}
                ]
        }

        self.assertEqual(expected, actual)


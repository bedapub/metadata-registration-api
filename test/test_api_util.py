import unittest

from metadata_registration_api.api import api_utils


class TestAPI_Util(unittest.TestCase):

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

        e = api_utils.json_entries_to_objs(entities, mapper, key_name="prop", value_name="value")
        actual = {entry.name: entry.form_format() for entry in e}

        expected = {
            "name": "test name", "datafiles":
                [
                    {"datafile": {"path": "/pstore/", "method": "count"}},
                    {"datafile": {"path": "/pstore/", "method": "count"}}
                ]
        }

        self.assertEqual(expected, actual)


import unittest

from metadata_registration_api.api.api_utils import MetaInformation


class TestAPIUtil(unittest.TestCase):
    def test_meta_information_empty_change_log(self):
        state = "Initial test state"

        m = MetaInformation(state=state)

        actual_json = m.to_json()
        expected_json = {"state": state, "change_log": []}

        self.assertEqual(expected_json, actual_json)

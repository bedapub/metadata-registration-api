from flask_restx import Namespace, Resource
from flask_restx import reqparse

from werkzeug.exceptions import NotFound

from metadata_registration_lib.api_utils import reverse_map

from metadata_registration_api.api.api_utils import get_property_map
from metadata_registration_api.mongo_utils import (
    find_study_id_from_lvl1_uuid,
    find_study_id_and_lvl1_uuid_from_lvl2_uuid,
)

api = Namespace("IDs", description="IDs and UUIDs related operations")


lvl_1_uuid_param = {
    "type": str,
    "location": "args",
    "help": "UUID of level 1 entity (ex: dataset_uuid)",
    "required": True,
}
lvl_2_uuid_param = {
    "type": str,
    "location": "args",
    "help": "UUID of level 2 entity (ex: pe_uuid)",
    "required": True,
}
lvl1_prop_name_param = {
    "type": str,
    "location": "args",
    "help": "Property name (singular) of level 1 entity (ex: dataset)",
    "default": "dataset",
    "required": True,
}
lvl2_prop_name_param = {
    "type": str,
    "location": "args",
    "help": "Property name (singular) of level 2 entity (ex: process_event)",
    "default": "process_event",
    "required": True,
}


# Routes
# ----------------------------------------------------------------------------------------------------------------------


@api.route("/study_id/get_from_lvl1_uuid")
class ApiIdLvl1(Resource):
    _get_parser = reqparse.RequestParser()
    _get_parser.add_argument("lvl1_uuid", **lvl_1_uuid_param)
    _get_parser.add_argument("lvl1_prop_name", **lvl1_prop_name_param)

    @api.doc(parser=_get_parser)
    @api.response("200", "Success")
    def get(self):
        """Find parent study id given a lvl1_uuid (ex: dataset_uuid)"""
        args = self._get_parser.parse_args()
        lvl1_uuid = args["lvl1_uuid"]
        lvl1_prop_name = args["lvl1_prop_name"].lower()

        prop_name_to_id = get_property_map(key="name", value="id")

        study_id = find_study_id_from_lvl1_uuid(
            lvl1_prop_name, lvl1_uuid, prop_name_to_id
        )

        if study_id is not None:
            return {"study_id": study_id}
        else:
            raise NotFound(f"{lvl1_prop_name} with uuid {lvl1_uuid} not found")


@api.route("/study_id_and_lvl1/get_from_lvl2_uuid")
class ApiIdLvl2(Resource):
    _get_parser = reqparse.RequestParser()
    _get_parser.add_argument("lvl2_uuid", **lvl_2_uuid_param)
    _get_parser.add_argument("lvl1_prop_name", **lvl1_prop_name_param)
    _get_parser.add_argument("lvl2_prop_name", **lvl2_prop_name_param)

    @api.doc(parser=_get_parser)
    @api.response("200", "Success")
    def get(self):
        """Find parent study id given a lvl1_uuid (ex: dataset_uuid)"""
        args = self._get_parser.parse_args()
        lvl2_uuid = args["lvl2_uuid"]
        lvl1_prop_name = args["lvl1_prop_name"].lower()
        lvl2_prop_name = args["lvl2_prop_name"].lower()

        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        study_id, lvl1_uuid = find_study_id_and_lvl1_uuid_from_lvl2_uuid(
            lvl1_prop=lvl1_prop_name,
            lvl2_prop=lvl2_prop_name,
            lvl2_uuid=lvl2_uuid,
            prop_name_to_id=prop_name_to_id,
            prop_id_to_name=prop_id_to_name,
        )

        if study_id is not None and lvl1_uuid is not None:
            return {"study_id": study_id, "lvl1_uuid": lvl1_uuid}
        else:
            raise NotFound(f"{lvl2_prop_name} with uuid {lvl2_uuid} not found")

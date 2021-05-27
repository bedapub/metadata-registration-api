from datetime import datetime

from flask import current_app as app
from flask_restx import Namespace, Resource, fields, marshal
from flask_restx import reqparse, inputs

from metadata_registration_lib.api_utils import FormatConverter
from metadata_registration_api.es_utils import (
    index_study,
    remove_study_from_index,
)
from metadata_registration_api.api.api_utils import (MetaInformation, ChangeLog,
    get_property_map)
from .api_props import property_model_id
from .decorators import token_required
from ..errors import IdenticalPropertyException, RequestBodyException
from ..model import Study

api = Namespace("Studies", description="Study related operations")

# Model definition
# ----------------------------------------------------------------------------------------------------------------------

entry_model = api.model("Entry", {
    "property": fields.Nested(property_model_id),
    "value": fields.Raw()
})

entry_model_prop_id = api.model("Entry (property collapsed)", {
    "property": fields.String(attribute='property.id', example="Property Object Id"),
    "value": fields.Raw()
})

entry_model_form_format = api.model("Entry (form format)", {
    "property_name_1": fields.Raw(example="Some value"),
    "property_name_2": fields.Raw(example="Some value")
})

change_log = api.model("Change Log", {
    "user_id": fields.String(),
    "manual_user": fields.String(),
    "action": fields.String(),
    "timestamp": fields.DateTime()
})

meta_information_model = api.model("Metadata Information", {
    "state": fields.String(),
    "deprecated": fields.Boolean(),
    "change_log": fields.List(fields.Nested(change_log))
})

study_model = api.model("Study", {
    "entries": fields.List(fields.Nested(entry_model)),
    "meta_information": fields.Nested(meta_information_model),
    "id": fields.String()
})

study_model_prop_id = api.model("Study (prop id)", {
    "entries": fields.List(fields.Nested(entry_model_prop_id)),
    "meta_information": fields.Nested(meta_information_model),
    "id": fields.String()
})

study_model_form_format = api.model("Study (form format)", {
    "entries": fields.Nested(entry_model_form_format),
    "meta_information": fields.Nested(meta_information_model),
    "id": fields.String()
})

nested_study_entry_model = api.model("Nested study entry", {
    "entries": fields.List(fields.Nested(entry_model)),
    "entry_format": fields.String(example="api", description="Format used for entries (api or form)"),
    "form_name": fields.String(example="form_name", required=True),
    "manual_meta_information": fields.Raw()
})

nested_study_entry_model_prop_id = api.model("Nested study entry (prop id)", {
    "entries": fields.List(fields.Nested(entry_model_prop_id)),
    "entry_format": fields.String(example="api", description="Format used for entries (api or form)"),
    "form_name": fields.String(example="form_name", required=True),
    "manual_meta_information": fields.Raw()
})

study_add_model = api.inherit("Add Study", nested_study_entry_model, {
    "initial_state": fields.String(default="GenericState", required=True, description="The initial state name"),
})

# Common parser params
# ----------------------------------------------------------------------------------------------------------------------
entry_format_param = {
    "type": str,
    "location": "args",
    "choices": ("api", "form"),
    "default": "api",
    "help": "Format used for entries (api or form)"
}

complete_param = {
    "type": inputs.boolean,
    "default": False,
    "help": "Boolean indicator to remove an entry instead of deprecating it (cannot be undone)"
}

properties_id_only_param = {
    "type": inputs.boolean,
    "location": "args",
    "default": False,
    "help": "Boolean indicator which determines if the entries properties need to be reduced to their id"
}

# Routes
# ----------------------------------------------------------------------------------------------------------------------

@api.route("")
class ApiStudy(Resource):
    _delete_parser = reqparse.RequestParser()
    _delete_parser.add_argument("complete", **complete_param)

    _get_parser = reqparse.RequestParser()
    _get_parser.add_argument(
        "deprecated",
        type=inputs.boolean,
        location="args",
        default=False,
        help="Boolean indicator which determines if deprecated entries should be returned as well",
    )
    _get_parser.add_argument(
        "skip",
        type=int,
        location="args",
        default=0,
        help="Number of results which should be skipped"
    )
    _get_parser.add_argument(
        "limit",
        type=int,
        location="args",
        default=100,
        help="Number of results which should be returned"
    )
    _get_parser.add_argument("properties_id_only", **properties_id_only_param)
    _get_parser.add_argument("entry_format", **entry_format_param)

    @token_required
    @api.response("200 - api", "Success (API format)", [study_model])
    @api.response("200 - form", "Success (form format)", [study_model_form_format])
    @api.doc(parser=_get_parser)
    def get(self, user=None):
        """ Fetch a list with all entries """
        # Convert query parameters
        args = self._get_parser.parse_args()
        include_deprecate = args["deprecated"]

        res = Study.objects.skip(args["skip"])

        # Issue with limit(0) that returns 0 items instead of all of them
        if args["limit"] != 0:
            res = res.limit(args["limit"])

        if not include_deprecate:
            res = res.filter(meta_information__deprecated=False)

        if args["properties_id_only"] or args["entry_format"] == "form":
            marchal_model = study_model_prop_id
        else:
            marchal_model = study_model

        # Marshal studies
        study_json_list = marshal(list(res.select_related()), marchal_model)

        if args["entry_format"] == "api":
            return study_json_list

        elif args["entry_format"] == "form":
            prop_map = get_property_map(key="id", value="name")
            for study_json in study_json_list:
                study_converter = FormatConverter(prop_map).add_api_format(study_json["entries"])
                study_json["entries"] = study_converter.get_form_format()

            return study_json_list

    @token_required
    @api.expect(study_add_model)
    def post(self, user=None):
        """ Add a new entry """

        payload = api.payload

        # 1. Split payload
        form_name = payload["form_name"]
        initial_state = payload["initial_state"]
        entries = payload["entries"]
        entry_format = payload.get("entry_format", "api")

        form_cls = app.form_manager.get_form_by_name(form_name=form_name)

        if initial_state == "rna_sequencing_biokit":
            initial_state = "BiokitUploadState"

        app.study_state_machine.load_state(name=initial_state)

        prop_map = get_property_map(key="name", value="id")

        # 2. Make sure to have both API and form format
        if entry_format == "api":
            try:
                if len(entries) != len({prop["property"] for prop in entries}):
                    raise IdenticalPropertyException("The entries cannot have several identical property values.")
            except TypeError as e:
                raise RequestBodyException("Entries has wrong format.") from e

            entries = {
                "api_format": entries,
                "form_format": validate_against_form(form_cls, form_name, entries)
            }

        else:
            validate_form_format_against_form(form_name, entries)
            entries = {
                "api_format": FormatConverter(prop_map).add_form_format(entries).get_api_format(),
                "form_format": entries
            }

        # 3. Check unicity of pseudo alternate pk in entries
        check_alternate_pk_unicity(entries=entries["form_format"], pseudo_apks=["study_id"], prop_map=prop_map)

        # 4. Evaluate new state of study by passing form data
        app.study_state_machine.create_study(**entries["form_format"])
        state = app.study_state_machine.current_state

        meta_info = MetaInformation(state=str(state))
        log = ChangeLog(user_id=user.id if user else None,
                        action="Created study",
                        timestamp=datetime.now(),
                        manual_user=payload.get("manual_meta_information", {}).get("user", None))
        meta_info.add_log(log)

        study_data = {"entries": entries["api_format"], "meta_information": meta_info.to_json()}

        # 5. Insert data into database
        study = Study(**study_data)
        study.save()

        # Index study on ES
        index_study_if_es(study, entries["form_format"], "add")

        return {"message": f"Study added", "id": str(study.id)}, 201


    @token_required
    @api.doc(parser=_delete_parser)
    def delete(self, user=None):
        """ Deprecates all entries """

        parser = reqparse.RequestParser()
        parser.add_argument("complete", **complete_param)
        args = parser.parse_args()

        force_delete = args["complete"]

        entry = Study.objects().all()
        if not force_delete:
            entry.update(deprecated=True)
            return {"message": "Deprecate all entries"}
        else:
            entry.delete()
            return {"message": "Delete all entries"}


@api.route("/id/<id>", strict_slashes=False)
@api.param("id", "The property identifier")
class ApiStudyId(Resource):
    _delete_parser = reqparse.RequestParser()
    _delete_parser.add_argument("complete", **complete_param)

    _get_parser = reqparse.RequestParser()
    _get_parser.add_argument("entry_format", **entry_format_param)
    _get_parser.add_argument("properties_id_only", **properties_id_only_param)

    @token_required
    @api.response("200 - api", "Success (API format)", study_model)
    @api.response("200 - form", "Success (form format)", study_model_form_format)
    @api.doc(parser=_get_parser)
    def get(self, id, user=None):
        """Fetch an entry given its unique identifier"""
        args = self._get_parser.parse_args()

        if args["properties_id_only"] or args["entry_format"] == "form":
            marchal_model = study_model_prop_id
        else:
            marchal_model = study_model

        study_json = marshal(Study.objects(id=id).get(), marchal_model)

        if args["entry_format"] == "api":
            return study_json

        elif args["entry_format"] == "form":
            prop_map = get_property_map(key="id", value="name")
            study_converter = FormatConverter(prop_map).add_api_format(study_json["entries"])
            study_json["entries"] = study_converter.get_form_format()
            return study_json

    @token_required
    @api.expect(nested_study_entry_model_prop_id)
    def put(self, id, user=None):
        """ Update an entry given its unique identifier """

        payload = api.payload

        # 1. Split payload
        study_id = id
        form_name = payload["form_name"]
        entries = payload["entries"]
        entry_format = payload.get("entry_format", "api")

        study = Study.objects(id=study_id).first()

        prop_map = get_property_map(key="name", value="id")

        # 1. Extract form name and create form from FormManager
        form_cls = app.form_manager.get_form_by_name(form_name=form_name)

        # 2. Make sure to have both API and form format
        if entry_format == "api":
            entries = {
                "api_format": entries,
                "form_format": validate_against_form(form_cls, form_name, entries)
            }

        else:
            validate_form_format_against_form(form_name, entries)
            entries = {
                "api_format": FormatConverter(prop_map).add_form_format(entries).get_api_format(),
                "form_format": entries
            }

        # 3. Check unicity of pseudo alternate pk in entries
        # check_alternate_pk_unicity(entries=entries["form_format"], pseudo_apks=["study_id"], prop_map=prop_map)

        # 4. Determine current state and evaluate next state
        state_name = str(study.meta_information.state)

        if state_name == "rna_sequencing_biokit":
            state_name = "BiokitUploadState"

        app.study_state_machine.load_state(name=state_name)
        app.study_state_machine.change_state(**entries["form_format"])
        new_state = app.study_state_machine.current_state

        # 5. Create and append meta information to the study
        meta_info = MetaInformation(
            state=state_name,
            change_log=study.meta_information.change_log
        )

        log = ChangeLog(action="Updated study",
                        user_id=user.id if user else None,
                        timestamp=datetime.now(),
                        manual_user=payload.get("manual_meta_information", {}).get("user", None))
        meta_info.state = str(new_state)
        meta_info.add_log(log)

        study_data = {"entries": entries["api_format"], "meta_information": meta_info.to_json()}

        # 6. Update data in database
        study.update(**study_data)

        # Index study on ES
        index_study_if_es(study, entries["form_format"], "update")

        return {"message": f"Update study"}

    @token_required
    @api.doc(parser=_delete_parser)
    def delete(self, id, user=None):
        """ Delete an entry given its unique identifier """
        args = self._delete_parser.parse_args()
        force_delete = args["complete"]

        entry = Study.objects(id=id).get()
        if not force_delete:
            entry.update(meta_information__deprecated=True)
            return {"message": "Deprecate entry"}
        else:
            entry.delete()
            # Update ES
            if app.config["ES"]["USE"]:
                remove_study_from_index(app.config, id)
            return {"message": "Delete entry"}


def validate_against_form(form_cls, form_name, entries):
    prop_map = get_property_map(key="id", value="name")

    form_data_json = FormatConverter(prop_map).add_api_format(entries).get_form_format()

    # 3. Validate data against form
    form_instance = form_cls()
    form_instance.process(data=form_data_json)

    if not form_instance.validate():
        raise RequestBodyException(f"Passed data did not validate with the form {form_name}: {form_instance.errors}")

    return form_data_json

def validate_form_format_against_form(form_name, form_data):
    form_cls = app.form_manager.get_form_by_name(form_name=form_name)
    form_instance = form_cls()
    form_instance.process(data=form_data)

    if not form_instance.validate():
        raise RequestBodyException(f"Passed data did not validate with the form {form_name}: {form_instance.errors}")


def index_study_if_es(study, entries, action):
    if app.config["ES"]["USE"]:
        study_to_index = marshal(study, study_model_prop_id)
        study_to_index["entries"] = entries
        index_study(app.config, study_to_index, action)


def update_study(study, study_converter, payload, message, user=None):
    """ Steps to update study state, metadata and upload to DB """
    # 1. Determine current state and evaluate next state
    state_name = str(study.meta_information.state)

    app.study_state_machine.load_state(name=state_name)
    app.study_state_machine.change_state(**study_converter.get_form_format())
    new_state = app.study_state_machine.current_state

    # 2. Update metadata / Create and append meta information to the study
    meta_info = MetaInformation(
        state=state_name,
        change_log=study.meta_information.change_log
    )

    if payload is not None:
        manual_user = payload.get("manual_meta_information", {}).get("user", None)
    else:
        manual_user = None

    log = ChangeLog(action=message,
                    user_id=user.id if user else None,
                    timestamp=datetime.now(),
                    manual_user=manual_user)
    meta_info.state = str(new_state)
    meta_info.add_log(log)

    study_data = {
        "entries": study_converter.get_api_format(),
        "meta_information": meta_info.to_json()
    }

    # 3. Update data in database
    study.update(**study_data)

    # Index study on ES
    index_study_if_es(study, study_converter.get_form_format(), "update")



def check_alternate_pk_unicity(entries, pseudo_apks, prop_map):
    """
    Another dirty mongoDB aggregation to enforce unicity of certain entry properties.
    """
    for prop_name in pseudo_apks:
        prop_id = prop_map[prop_name]
        pipeline = [
            # Keep the wanted field
            {"$addFields": {
                prop_name: {
                    "$filter": {
                        "input":"$entries",
                        "as":"entry",
                        "cond":{"$eq": [{"$toString": "$$entry.property"}, prop_id]}
                    }
                }
            }},
            # Take first (and only) element of filtered entries
            {"$addFields": {prop_name: {"$arrayElemAt": [f"${prop_name}", 0]}}},
            # Get the actual entry value
            {"$addFields": {prop_name: f"${prop_name}.value"}},
            {"$group": {"_id": 1, prop_name: {"$addToSet": f"${prop_name}"}}},
            {"$project": {prop_name: 1, "_id": 0}}
        ]

        existing_list = Study.objects().aggregate(pipeline).next()[prop_name]
        if entries[prop_name] in existing_list:
            raise Exception(f"The property '{prop_name}' needs to be unique across all studies")

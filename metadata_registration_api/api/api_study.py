from datetime import datetime
import os
from urllib.parse import urljoin

from flask import current_app as app
from flask_restx import Namespace, Resource, fields
from flask_restx import reqparse, inputs
from wtforms import ValidationError

from . import api_utils
from .api_props import property_model_id
from .decorators import token_required
from .. import my_utils
from ..errors import IdenticalPropertyException
from ..model import Study

api = Namespace("Studies", description="Study related operations")

# Model definition
# ----------------------------------------------------------------------------------------------------------------------

entry_model = api.model("Entry", {
    "property": fields.Nested(property_model_id),
    "value": fields.Raw()
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
})

study_model_id = api.inherit("Study with id", study_model, {
    "id": fields.String()
})

field_add_model = api.model("Add Field", {
    "property": fields.String(example="Property Object Id"),
    "value": fields.Raw()
})

study_add_model = api.model("Add Study", {
    "form_name": fields.String(example="Form Object Id", required=True),
    "initial_state": fields.String(default="generic_state", required=True, description="The initial state name"),
    "entries": fields.List(fields.Nested(field_add_model)),
    "manual_meta_information": fields.Raw()
})

study_modify_model = api.inherit("Modify study model", study_add_model, {
    "id": fields.String()
})


# Routes
# ----------------------------------------------------------------------------------------------------------------------

@api.route("")
class ApiStudy(Resource):
    _delete_parser = reqparse.RequestParser()
    _delete_parser.add_argument("complete",
                                type=inputs.boolean,
                                default=False,
                                help="Boolean indicator to remove an entry instead of deprecating it (cannot be undone)"
                                )

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

    # @token_required
    @api.marshal_with(study_model_id)
    @api.expect(parser=_get_parser)
    def get(self):
        """ Fetch a list with all entries """
        # Convert query parameters
        args = self._get_parser.parse_args()
        include_deprecate = args["deprecated"]

        if not include_deprecate:
            res = Study.objects(meta_information__deprecated=False)[args["skip"]:args["skip"]+args["limit"]].all()
        else:
            # Include entries which are deprecated
            res = Study.objects[args["skip"]:args["skip"]+args["limit"]]
            return list(res)

    @token_required
    @api.expect(study_add_model)
    def post(self, user=None):
        """ Add a new entry """

        payload = api.payload

        # 1. Split payload
        form_name = payload["form_name"]
        initial_state = payload["initial_state"]
        entries = payload["entries"]

        try:
            form_cls = app.form_manager.get_form_by_name(form_name=form_name)
        except Exception as e:
            raise Exception("Could not load form" + str(e))
        try:
            app.study_state_machine.load_initial_state(name=initial_state)
        except Exception as e:
            raise Exception("Could not initialize state machine" + str(e))

        # 2. Convert submitted data into form compatible format

        if len(entries) != len({prop["property"] for prop in entries}):
            raise IdenticalPropertyException("The entries cannot have several identical property values.")

        form_data_json = validate_against_form(form_cls, form_name, entries)

        # 4. Evaluate new state of study by passing form data
        state = app.study_state_machine.eval_next_state(**form_data_json)

        meta_info = api_utils.MetaInformation(state=state)
        log = api_utils.ChangeLog(user_id=user.id if user else None,
                                  action="Created study",
                                  timestamp=datetime.now(),
                                  manual_user=payload.get("manual_meta_information", {}).get("user", None))
        meta_info.add_log(log)

        entry_data = {"entries": entries, "meta_information": meta_info.to_json()}

        # 6. Insert data into database
        entry = Study(**entry_data)
        entry.save()
        app.study_state_machine.change()
        return {"message": f"Study added", "id": str(entry.id)}, 201


    @token_required
    @api.expect(parser=_delete_parser)
    def delete(self, user=None):
        """ Deprecates all entries """

        parser = reqparse.RequestParser()
        parser.add_argument("complete", type=inputs.boolean, default=False)
        args = parser.parse_args()

        force_delete = args["complete"]

        entry = Study.objects().all()
        # if not force_delete:
        #     entry.update(deprecated=True)
        #     return {"message": "Deprecate all entries"}
        # else:
        entry.delete()
        return {"message": "Delete all entries"}


@api.route("/id/<id>")
@api.route("/id/<id>/")
@api.param("id", "The property identifier")
class ApiStudy(Resource):
    _delete_parser = reqparse.RequestParser()
    _delete_parser.add_argument("complete",
                               type=inputs.boolean,
                               default=False,
                               help="Boolean indicator to remove an entry instead of deprecating it (cannot be undone)"
                               )

    # @token_required
    @api.marshal_with(study_model_id)
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        return Study.objects(id=id).get()

    @token_required
    @api.expect(study_modify_model)
    def put(self, id, user=None):
        """ Update an entry given its unique identifier """

        payload = api.payload

        study_id = payload["id"]
        form_name = payload["form_name"]
        entries = payload["entries"]

        entry = Study.objects(id=study_id).first()

        # 1. Extract form name and create form from FormManager
        form_cls = app.form_manager.get_form_by_name(form_name=form_name)

        # 2. Convert submitted data in form format
        form_data_json = validate_against_form(form_cls, form_name, entries)
        # 4. Determine current state and evaluate next state
        app.study_state_machine.load_state(payload["meta_information"]["state"])
        state = app.study_state_machine.eval_next_state(**form_data_json)

        # 5. Update metadata
        # 5. Create and append meta information to the entry

        meta_info = api_utils.MetaInformation(**entry.metadata)

        log = api_utils.ChangeLog(action="Changed study",
                                  user_id= user.id if user else None,
                                  timestamp=datetime.now(),
                                  manual_user=payload.get("manual_meta_information", {}).get("user", None))
        meta_info.state = state
        meta_info.add_log(log)

        entry_data = {"entries": entries, "meta_information": meta_info.to_json()}

        # 6. Update data in database
        entry.update(**entry_data)
        app.study_state_machine.change()
        return {"message": f"Update entry"}


    @token_required
    @api.expect(parser=_delete_parser)
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
            return {"message": "Delete entry"}


def validate_against_form(form_cls, form_name, entries):
    property_url = urljoin(app.config["URL"], os.environ["API_EP_PROPERTY"])
    prop_map = my_utils.map_key_value(url=property_url, key="id", value="name")

    form_data_json = api_utils.json_input_to_form_format(json_data=entries, mapper=prop_map)

    # 3. Validate data against form
    form_instance = form_cls(**form_data_json)

    if not form_instance.validate():
        raise ValidationError(f"Passed data did not validate with the form {form_name}: {form_instance.errors}")

    return form_data_json


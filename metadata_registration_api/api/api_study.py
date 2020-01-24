from flask import current_app
from flask_restx import Namespace, Resource, fields
from flask_restx import reqparse, inputs

from ..model import Study
from .api_props import property_model_id
from .decorators import token_required

from wtforms import ValidationError

api = Namespace("Studies", description="Study related operations")

# Model definition
# ----------------------------------------------------------------------------------------------------------------------

field_model = api.model("Field", {
    "property": fields.Nested(property_model_id),
    "value": fields.Raw()
})

status_model = api.model("Status", {
    "name": fields.String()
})

study_model = api.model("Study", {
    "label": fields.String(description="A human readable description of the entry"),
    "name": fields.String(description="The unique name of the entry (in snake_case)"),
    "entries": fields.List(fields.Nested(field_model)),
    "status": fields.Nested(status_model),
    "deprecated": fields.Boolean(default=False)
})

study_model_id = api.inherit("Study with id", study_model, {
    "id": fields.String()
})

field_add_model = api.model("Add Field", {
    "property": fields.String(example="Property Object Id"),
    "value": fields.Raw()
})

study_add_model = api.model("Add Study", {
    # "label": fields.String(description="A human readable description of the entry"),
    # "name": fields.String(description="The unique name of the entry (in snake_case)"),
    "form_name": fields.String(example="Form Object Id"),
    "entries": fields.List(fields.Nested(field_add_model)),
    # "metadata": fields.Nested(status_model),
    # "deprecated": fields.Boolean(default=False)
})


# Routes
# ----------------------------------------------------------------------------------------------------------------------

@api.route("/")
class ApiStudy(Resource):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument(
        "deprecated",
        type=inputs.boolean,
        location="args",
        default=False,
        help="Boolean indicator which determines if deprecated entries should be returned as well",
    )

    # @token_required
    @api.marshal_with(study_model_id)
    @api.expect(parser=get_parser)
    def get(self):
        """ Fetch a list with all entries """
        # Convert query parameters
        args = self.get_parser.parse_args()
        include_deprecate = args["deprecated"]

        if not include_deprecate:
            res = Study.objects(deprecated=False).all()
        else:
            # Include entries which are deprecated
            res = Study.objects().all()
        return list(res)

    @token_required
    @api.expect(study_add_model)
    def post(self, user):
        """ Add a new entry """
        payload = api.payload

        # 1. Extract form name from payload
        form_name = payload["form_name"]

        # 2. Get form from FormManager by name
        form_cls = current_app.form_manager.get_form(form_name=form_name)

        # 3. Convert submitted data into form compatible format
        entries = payload["entries"]

        import requests
        props = requests.get("http://127.0.0.1:5001/properties/")
        prop_map = {prop["id"]: prop["name"] for prop in props.json()}

        form_data = []
        for entry in entries:
            form_data[prop_map[entry["property"]]] = entry["value"]

        # 4. Validate data against form
        form_instance = form_cls(**form_data)

        if not form_instance.validate():
            raise ValidationError(form_instance.errors)

        # 5. evaluate new state of study pass all information
        state = ""

        # 6. Convert submitted data into document compatible format
        import requests
        props = requests.get(url= "", heards={"x-Fields": ["name", "id"]})
        prop_map = {entry["name"]: entry["id"] for entry in props.items()}

        entries = []
        for prop_name, value in form_data.items():
            entries.append({
                "entry": prop_map[prop_name],
                "value": value
            })

        # 7. Append metadata
        from datetime import datetime
        metadata = {
            "created": datetime.now(),
            "last_change": datetime.now(),
            "user": user.id,
            "state": state,
            "history": []
        }

        db_data = {"entries": entries, "metadata": metadata}
        # 8. Insert data into database
        entry = Study(**db_data)
        entry.save()
        return {"message": f"Study added"}, 201


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
    @api.expect(study_add_model)
    def put(self, user, id):
        """ Update an entry given its unique identifier """
        entry = Study.objects(id=id).get()
        entry.update(**api.payload)
        return {"message": f"Update entry '{entry.name}'"}

    @token_required
    @api.expect(parser=_delete_parser)
    def delete(self, user, id):
        """ Delete an entry given its unique identifier """
        args = self._delete_parser.parse_args()
        force_delete = args["complete"]

        entry = Study.objects(id=id).get()
        if not force_delete:
            entry.update(deprecated=True)
            return {"message": f"Deprecate entry '{entry.name}'"}
        else:
            entry.delete()
            return {"message": f"Delete entry {entry.name}"}

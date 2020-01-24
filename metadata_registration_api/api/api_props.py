from flask_restx import Namespace, Resource, fields
from flask_restx import reqparse, inputs

from ..model import Property
from .api_ctrl_voc import ctrl_voc_model_id
from .decorators import token_required

api = Namespace("Properties", description="Property related operations")

# ----------------------------------------------------------------------------------------------------------------------
cv_model_add = api.model("Add Vocabulary Type", {
    "data_type": fields.String(description="The data type of the entry"),
    "controlled_vocabulary": fields.String(example='Controlled Vocabulary ObjectId')
})

property_add_model = api.model("Add Property", {
    "label": fields.String(description="A human readable description of the entry"),
    "name": fields.String(description="The unique name of the entry (in snake_case)"),
    "level": fields.String(description="The level the property is associated with (e.g. Study, Sample, ...)"),
    "value_type": fields.Nested(cv_model_add),
    "synonyms": fields.List(fields.String(description="Alternatives to the primary name")),
    "description": fields.String(description="A detailed description of the intended use", default=""),
    "deprecated": fields.Boolean(default=False)
})

cv_model = api.model("Vocabulary Type", {
    "data_type": fields.String(description="The data type of the entry"),
    "controlled_vocabulary": fields.Nested(ctrl_voc_model_id)
})

property_model = api.model("Property", {
    "label": fields.String(description="A human readable description of the entry"),
    "name": fields.String(description="The unique name of the entry (in snake_case)"),
    "level": fields.String(description="The level the property is associated with (e.g. Study, Sample, ...)"),
    "value_type": fields.Nested(cv_model),
    "synonyms": fields.List(fields.String(description="Alternatives to the primary name")),
    "description": fields.String(description="A detailed description of the intended use", default=""),
    "deprecated": fields.Boolean(default=False)
})

property_model_id = api.inherit("Property with id", property_model, {
    "id": fields.String(attribute="id", description="The unique identifier of the entry"),
})

post_response_model = api.model("Post response", {
    "message": fields.String(),
    "id": fields.String(description="Id of inserted entry")
})


# ----------------------------------------------------------------------------------------------------------------------

@api.route("/")
class ApiProperties(Resource):
    _delete_parser = reqparse.RequestParser()
    _delete_parser.add_argument("complete",
                               type=inputs.boolean,
                               default=False,
                               help="Boolean indicator to remove an entry instead of deprecating it (cannot be undone)"
                               )

    get_parser = reqparse.RequestParser()
    get_parser.add_argument("deprecated",
                            type=inputs.boolean,
                            location="args",
                            default=False,
                            help="Boolean indicator which determines if deprecated entries should be returned as well",
                            )

    @api.marshal_with(property_model_id)
    @api.expect(parser=get_parser)
    def get(self):
        """ Fetch a list with all entries """

        # Convert query parameters
        args = self.get_parser.parse_args()
        include_deprecate = args["deprecated"]

        if not include_deprecate:
            entries = Property.objects(deprecated=False).all()
        else:
            # Include entries which are deprecated
            entries = Property.objects().all()
        return list(entries)

    @token_required
    @api.expect(property_add_model)
    @api.response(201, "Success", post_response_model)
    def post(self, user):
        """ Add a new entry

            The name has to be unique and is internally used as a variable name. The passed string is
            preprocessed before it is inserted into the database. Preprocessing: All characters are converted to
            lower case, the leading and trailing white spaces are removed, and intermediate white spaces are replaced
            with underscores ("_").

            Do not pass a unique identifier since it is generated internally.

            synonyms (optional)

            deprecated (default=False)

            If a data type other than "cv" is added, the controlled_vocabullary is not considered.
        """

        entry = Property(**api.payload)

        # Ensure that a passed controlled vocabulary is valid
        validate_controlled_vocabulary(entry)

        entry = entry.save()
        return {"message": f"Add entry '{entry.name}'",
                "id": str(entry.id)}, 201

    @token_required
    @api.expect(parser=_delete_parser)
    def delete(self, user):
        """ Deprecates all entries """

        parser = reqparse.RequestParser()
        parser.add_argument("complete", type=inputs.boolean, default=False)
        args = parser.parse_args()

        force_delete = args["complete"]

        entry = Property.objects().all()
        if not force_delete:
            entry.update(deprecated=True)
            return {"message": "Deprecate all entries"}
        else:
            entry.delete()
            return {"message": "Delete all entries"}


@api.route("/id/<id>")
@api.route("/id/<id>/")
@api.param("id", "The property identifier")
class ApiProperty(Resource):
    _delete_parser = reqparse.RequestParser()
    _delete_parser.add_argument("complete",
                               type=inputs.boolean,
                               default=False,
                               help="Boolean indicator to remove an entry instead of deprecating it (cannot be undone)"
                               )

    @api.marshal_with(property_model_id)
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        return Property.objects(id=id).get()

    @token_required
    @api.expect(property_model)
    def put(self, user, id):
        """ Update entry given its unique identifier """
        entry = Property.objects(id=id).first()
        entry.update(**api.payload)
        return {"message": f"Update entry '{entry.name}'"}

    @token_required
    @api.expect(parser=_delete_parser)
    def delete(self, user, id):
        """ Deprecates an entry given its unique identifier """

        parser = reqparse.RequestParser()
        parser.add_argument("complete", type=inputs.boolean, default=False)
        args = parser.parse_args()

        force_delete = args["complete"]

        entry = Property.objects(id=id).get()
        if not force_delete:
            entry.update(deprecated=True)
            return {"message": f"Deprecate entry '{entry.name}'"}
        else:
            entry.delete()
            return {"message": f"Delete entry '{entry.name}'"}


def validate_controlled_vocabulary(entry):
    if entry.value_type and entry.value_type.data_type != "ctrl_voc":
        entry.value_type.controlled_vocabulary = None

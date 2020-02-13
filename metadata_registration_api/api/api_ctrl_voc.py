from flask_restx import Namespace, Resource, fields
from flask_restx import reqparse, inputs

from database_model.model import ControlledVocabulary
from .decorators import token_required

api = Namespace("Controlled Vocabularies", description="Controlled vocabulary related operations")

# Model definition
# ----------------------------------------------------------------------------------------------------------------------

cv_item_model = api.model("CV item", {
    "label": fields.String(description="Human readable name of the entry"),
    "name": fields.String(description="Internal representation of the entry (in snake_case)"),
    "description": fields.String(description="Detailed explanation of the intended use"),
    "synonyms": fields.List(fields.String())
})

ctrl_voc_model = api.model("Controlled Vocabulary", {
    "label": fields.String(description="Human readable name of the entry"),
    "name": fields.String(description="Internal representation of the entry (in snake_case)"),
    "description": fields.String(description="Detailed description of the intended use", default=""),
    "items": fields.List(fields.Nested(cv_item_model, skip_none=True)),
    "deprecated": fields.Boolean(description="Indicator, if the entry is no longer used.", default=False)
})

ctrl_voc_model_id = api.inherit("Controlled Vocabulary with id", ctrl_voc_model, {
    "id": fields.String(attribute="pk", description="Unique identifier of the entry"),
})

post_response_model = api.model("Post response", {
    "message": fields.String(),
    "id": fields.String(description="Id of inserted entry")
})


# Routes
# ----------------------------------------------------------------------------------------------------------------------

@api.route("")
class ApiControlledVocabulary(Resource):
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

    @api.marshal_with(ctrl_voc_model_id)
    @api.expect(parser=get_parser)
    def get(self):
        """ Fetch a list with all entries """

        # Convert query parameters
        args = self.get_parser.parse_args()
        include_deprecate = args["deprecated"]

        if not include_deprecate:
            # Select only active entries
            res = ControlledVocabulary.objects(deprecated=False).all()
        else:
            # Include deprecated entries
            res = ControlledVocabulary.objects().all()
        return list(res)

    @token_required
    @api.expect(ctrl_voc_model)
    @api.response(201, "Success", post_response_model)
    def post(self, user):
        """ Add a new entry """
        entry = ControlledVocabulary(**api.payload)
        entry = entry.save()
        return {"message": f"Add entry '{entry.name}'",
                "id": str(entry.id)}, 201

    @token_required
    @api.expect(parser=_delete_parser)
    def delete(self, user):
        """ Delete all entries"""

        args = self._delete_parser.parse_args()

        force_delete = args["complete"]

        entry = ControlledVocabulary.objects().all()
        if not force_delete:
            entry.update(deprecated=True)
            return {"message": "Deprecate all entries"}
        else:
            entry.delete()
            return {"message": "Delete all entries"}


@api.route("/id/<id>")
@api.route("/id/<id>/")
@api.param("id", "The property identifier")
class ApiControlledVocabulary(Resource):
    _delete_parser = reqparse.RequestParser()
    _delete_parser.add_argument("complete",
                               type=inputs.boolean,
                               default=False,
                               help="Boolean indicator to remove an entry instead of deprecating it (cannot be undone)"
                               )

    @api.marshal_with(ctrl_voc_model_id)
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        return ControlledVocabulary.objects(id=id).get()

    @token_required
    @api.expect(ctrl_voc_model)
    def put(self, user, id):
        """ Update an entry given its unique identifier """
        entry = ControlledVocabulary.objects(id=id).get()
        entry.update(**api.payload)
        return {"message": f"Update entry '{entry.name}'"}

    @token_required
    @api.expect(parser=_delete_parser)
    def delete(self, user, id):
        """ Delete an entry given its unique identifier """

        args = self._delete_parser.parse_args()

        force_delete = args["complete"]

        entry = ControlledVocabulary.objects(id=id).get()
        if not force_delete:
            entry.update(deprecated=True)
            return {"message": f"Deprecate entry '{entry.name}'"}
        else:
            entry.delete()
            return {"message": f"Delete entry '{entry.name}'"}

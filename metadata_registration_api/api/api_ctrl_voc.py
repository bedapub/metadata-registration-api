from flask_restx import Namespace, Resource, fields
from flask_restx import reqparse, inputs
from mongoengine.errors import ValidationError

from metadata_registration_api.model import ControlledVocabulary
from .decorators import token_required

api = Namespace(
    "Controlled Vocabularies", description="Controlled vocabulary related operations"
)

# Model definition
# ----------------------------------------------------------------------------------------------------------------------

cv_item_model = api.model(
    "CV item",
    {
        "label": fields.String(description="Human readable name of the entry"),
        "name": fields.String(
            description="Internal representation of the entry (in snake_case)"
        ),
        "description": fields.String(
            description="Detailed explanation of the intended use"
        ),
        "synonyms": fields.List(fields.String()),
    },
)

ctrl_voc_model_no_items = api.model(
    "Controlled Vocabulary (no items)",
    {
        "label": fields.String(description="Human readable name of the entry"),
        "name": fields.String(
            description="Internal representation of the entry (in snake_case)"
        ),
        "description": fields.String(
            description="Detailed description of the intended use", default=""
        ),
        "deprecated": fields.Boolean(
            description="Indicator, if the entry is no longer used.", default=False
        ),
    },
)

ctrl_voc_model = api.inherit(
    "Controlled Vocabulary",
    ctrl_voc_model_no_items,
    {
        "items": fields.List(fields.Nested(cv_item_model, skip_none=True)),
    },
)

ctrl_voc_model_id_no_items = api.inherit(
    "Controlled Vocabulary (no items) with id",
    ctrl_voc_model_no_items,
    {
        "id": fields.String(
            attribute="pk", description="Unique identifier of the entry"
        ),
    },
)

ctrl_voc_model_id = api.inherit(
    "Controlled Vocabulary with id",
    ctrl_voc_model,
    {
        "id": fields.String(
            attribute="pk", description="Unique identifier of the entry"
        ),
    },
)

post_response_model = api.model(
    "Post response",
    {
        "message": fields.String(),
        "id": fields.String(description="Id of inserted entry"),
    },
)


# Routes
# ----------------------------------------------------------------------------------------------------------------------


@api.route("")
class ApiControlledVocabulary(Resource):
    _delete_parser = reqparse.RequestParser()
    _delete_parser.add_argument(
        "complete",
        type=inputs.boolean,
        default=False,
        help="Boolean indicator to remove an entry instead of deprecating it (cannot be undone)",
    )

    get_parser = reqparse.RequestParser()
    get_parser.add_argument(
        "deprecated",
        type=inputs.boolean,
        location="args",
        default=False,
        help="Boolean indicator which determines if deprecated entries should be returned as well",
    )

    @api.marshal_with(ctrl_voc_model_id)
    @api.doc(parser=get_parser)
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
    def post(self, user=None):
        """ Add a new entry """
        entry = ControlledVocabulary(**api.payload)
        entry = entry.save()
        return {"message": f"Add entry '{entry.name}'", "id": str(entry.id)}, 201

    @token_required
    @api.doc(parser=_delete_parser)
    def delete(self, user=None):
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


@api.route("/id/<id>", strict_slashes=False)
@api.param("id", "The property identifier")
class ApiControlledVocabularyId(Resource):
    _delete_parser = reqparse.RequestParser()
    _delete_parser.add_argument(
        "complete",
        type=inputs.boolean,
        default=False,
        help="Boolean indicator to remove an entry instead of deprecating it (cannot be undone)",
    )

    @api.marshal_with(ctrl_voc_model_id)
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        return ControlledVocabulary.objects(id=id).get()

    @token_required
    @api.expect(ctrl_voc_model)
    def put(self, id, user=None):
        """ Update an entry given its unique identifier """
        entry = ControlledVocabulary.objects(id=id).get()
        entry_old_json = api.marshal(entry, ctrl_voc_model_id)

        entry.modify(**api.payload)
        try:
            entry.validate()
        except ValidationError as error:
            # TODO: Dirty, need a better way to validate BEFORE uploading to DB
            # Currently upload to DB, validate, re-upload old if validation fails
            entry_old = ControlledVocabulary(**entry_old_json)
            entry_old.save(validate=False)
            raise error
        return {"message": f"Update entry '{entry.name}'"}

    @token_required
    @api.doc(parser=_delete_parser)
    def delete(self, id, user=None):
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


@api.route("/map_items")
class ApiControlledVocabularyItemsMap(Resource):
    _get_parser = reqparse.RequestParser()
    _get_parser.add_argument(
        "key",
        type=str,
        location="args",
        default="name",
        help="Key of the map.",
    )
    _get_parser.add_argument(
        "value",
        type=str,
        location="args",
        default="label",
        help="Value of the map.",
    )

    @api.doc(parser=_get_parser)
    def get(self):
        """ Get a map for CV items: cv_name: {item_key; item_value} """
        args = self._get_parser.parse_args()

        key = args["key"]
        value = args["value"]

        cv_entries = ControlledVocabulary.objects(deprecated=False).only(
            "name", "items__name", "items__label"
        )

        cv_items_map = {}
        for cv in cv_entries:
            cv_items_map[cv["name"]] = {item[key]: item[value] for item in cv["items"]}

        return cv_items_map

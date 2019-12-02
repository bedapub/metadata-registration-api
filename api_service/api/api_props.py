from bson import ObjectId

from flask_restplus import Namespace, Resource, fields
from flask_restplus import reqparse, inputs

from api_service.model import Property
from api_service.model import ControlledVocabulary


from bson.errors import InvalidId, InvalidDocument


api = Namespace('Properties', description='Property related operations')

cv_model = api.model("Vocabulary Type", {
    'data_type': fields.String(description="The data type of the entry"),
    'controlled_vocabulary': fields.String(description="The unique identifier of the controlled vocabulary")
})

entry_model = api.model('Property', {
    'label': fields.String(description='A human readable description of the entry'),
    'name': fields.String(description='The unique name of the entry (in snake_case)'),
    'level': fields.String(description='The level the property is associated with (e.g. Study, Sample, ...)'),
    'vocabulary_type': fields.Nested(cv_model),
    'synonyms': fields.List(fields.String(description='Alternatives to the priamry name')),
    'description': fields.String(description='A detailed description of the intended use', default=''),
    'deprecate': fields.Boolean(default=False)
})

entry_model_id = api.inherit('Property with id', entry_model, {
    'id': fields.String(attribute='pk', description='The unique identifier of the entry'),
})

@api.route('/')
class ApiProperties(Resource):

    @api.marshal_with(entry_model_id)
    @api.doc(params={'deprecate': "Boolean indicator which determines if deprecated entries should be returned as "
                                  "well  (default False)"})
    def get(self):
        """ Fetch a list with all entries """

        # Convert query parameters
        parser = reqparse.RequestParser()
        parser.add_argument('deprecate', type=inputs.boolean, location="args", default=False)
        args = parser.parse_args()

        include_deprecate = args['deprecate']

        if not include_deprecate:
            entries = Property.objects(deprecate=False).all()
        else:
            # Include entries which are deprecated
            entries = Property.objects().all()
        return list(entries)

    @api.expect(entry_model)
    def post(self):
        """ Add a new entry

            The name has to be unique and is internally used as a variable name. The passed string is
            preprocessed before it is inserted into the database. Preprocessing: All characters are converted to
            lower case, the leading and trailing white spaces are removed, and intermediate white spaces are replaced
            with underscores ("_").

            Do not pass a unique identifier since it is generated internally.

            synonyms (optional)

            deprecate (default=False)

            If a data type other than "cv" is added, the controlled_vocabullary is not considered.
        """

        entry = Property(**api.payload)

        # Ensure that a passed controlled vocabulary is valid
        validate_controlled_vocabulary(entry)

        entry.save()
        return {"message": "Add entry '{}'".format(entry.name)}, 201


@api.route('/id/<id>')
@api.param('id', 'The property identifier')
class ApiProperty(Resource):

    @api.marshal_with(entry_model_id)
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        return Property.objects(id=id).get()

    @api.expect(entry_model)
    def put(self, id):
        """ Update entry given its unique identifier """
        entry = Property.objects(id=id).first()
        entry.update(**api.payload)
        return {'message': "Update entry '{}'".format(entry.name)}

    @api.doc(params={'complete': "Boolean indicator to remove an entry instead of deprecating it (cannot be undone) "
                                 "(default False)"})
    def delete(self, id):
        """ Deprecates an entry given its unique identifier """

        parser = reqparse.RequestParser()
        parser.add_argument('complete', type=inputs.boolean, default=False)
        args = parser.parse_args()

        force_delete = args['complete']

        entry = Property.objects(id=id).get()
        if not force_delete:
            entry.update(deprecate=True)
            return {'message': "Deprecate entry '{}'".format(entry.name)}
        else:
            entry.delete()
            return {'message': "Delete entry '{}'".format(entry.name)}


def validate_controlled_vocabulary(entry):

    if entry.vocabulary_type:
        cv_data_type = entry.vocabulary_type.data_type
    else:
        return

    # If property is a controlled vocabulary
    if cv_data_type == "cv":
        cv = entry.vocabulary_type.controlled_vocabulary

        # TODO: Should we support name of controlled vocabulary?

        if ControlledVocabulary.objects(id=cv.pk).count() != 1:
            raise InvalidDocument(f"Controlled_vocabulary with id={cv.pk} was not found")
    # If a vocabulary type is given but is not cv, remove controlled_vocabulary
    elif entry.vocabulary_type:
        entry.vocabulary_type.controlled_vocabulary = None


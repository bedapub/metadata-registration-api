from flask_restplus import Namespace, Resource, fields
from flask_restplus import reqparse, inputs

from api_service.model import ControlledVocabulary


api = Namespace('Controlled Vocabulary', description='Controlled vocabulary related operations')

cv_item_model = api.model("CV item", {
    'label': fields.String(description='Human readable name of the entry'),
    'name': fields.String(description='Internal representation of the entry (in snake_case)'),
    'description': fields.String(description="Detailed explanation of the intended use"),
    'synonyms': fields.List(fields.String())
})

property_model = api.model('Controlled Vocabulary', {
    'label': fields.String(description='Human readable name of the entry'),
    'name': fields.String(description='Internal representation of the entry (in snake_case)'),
    'description': fields.String(description='Detailed description of the intended use', default=''),
    'items': fields.List(fields.Nested(cv_item_model)),
    'deprecate': fields.Boolean(description="Indicator, if the entry is no longer used.", default=False)
})

property_model_id = api.inherit("Controlled Vocabulary with id", property_model, {
    'id': fields.String(attribute='pk', description='Unique identifier of the entry'),
})


@api.route('/')
class ApiControlledVocabulary(Resource):
    @api.marshal_with(property_model_id)
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
            # Select only active entries
            res = ControlledVocabulary.objects(deprecate=False).all()
        else:
            # Include deprecated entries
            res = ControlledVocabulary.objects().all()
        return list(res)

    @api.expect(property_model)
    def post(self):
        """ Add a new entry """
        p = ControlledVocabulary(**api.payload)
        p = p.save()
        return {"message": "Add entry '{}'".format(p.name),
                "id": str(p.id)}, 201


@api.route('/id/<id>')
@api.param('id', 'The property identifier')
class ApiControlledVocabulary(Resource):
    @api.marshal_with(property_model_id)
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        return ControlledVocabulary.objects(id=id).get()

    @api.expect(property_model)
    def put(self, id):
        """ Update an entry given its unique identifier """
        entry = ControlledVocabulary.objects(id=id).get()
        entry.update(**api.payload)
        return {'message': "Update entry '{}'".format(entry.name)}

    @api.doc(params={'complete': "Boolean indicator to remove an entry instead of deprecating it (cannot be undone) "
                                 "(default False)"})
    def delete(self, id):
        """ Delete an entry given its unique identifier """

        parser = reqparse.RequestParser()
        parser.add_argument('complete', type=inputs.boolean, default=False)
        args = parser.parse_args()

        force_delete = args['complete']

        entry = ControlledVocabulary.objects(id=id).get()
        if not force_delete:
            entry.update(deprecate=True)
            return {'message': "Deprecate entry '{}'".format(entry.name)}
        else:
            entry.delete()
            return {'message': "Delete entry {}".format(entry.name)}

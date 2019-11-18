from flask import request
from flask_restplus import Namespace, Resource, fields

from ..model import ControlledVocabulary


api = Namespace('Controlled Vocabulary', description='Controlled vocabulary related operations')


property_model = api.model('Controlled Vocabulary', {
    'id': fields.String(attribute='pk', description='Unique identifier of the entry'),
    'label': fields.String(description='Human readable description of the entry'),
    'primary_name': fields.String(description='Name of the entry (in snake_case)'),
    'synonyms': fields.List(fields.String(description='Alternatives to the primary name')),
    'description': fields.String(description='Detailed description of the intended use', default=''),
    'deprecate': fields.Boolean(description="Indicator, if the entry is no longer used.", default=False)
})


@api.route('/')
class ApiControlledVocabulary(Resource):
    @api.marshal_with(property_model)
    def get(self):
        """ Fetch a list with all entries

            query parameters:
            - deprecate: boolean: Indicate if deprecated entries should be returned as well (default False)
        """
        include_deprecate = request.args.get('deprecate', False)

        if not include_deprecate:
            res = ControlledVocabulary.objects(deprecate=False).all()
        else:
            res = ControlledVocabulary.objects().all()
        return list(res)

    @api.expect(property_model)
    def post(self):
        """ Add a new entry """
        p = ControlledVocabulary(**api.payload)
        p.save()
        return {"message": "Add entry '{}'".format(p.primary_name)}, 201


@api.route('/id/<id>')
@api.param('id', 'The property identifier')
class ApiControlledVocabulary(Resource):
    @api.marshal_with(property_model)
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        return ControlledVocabulary.objects(id=id).get()

    @api.expect(property_model)
    def put(self, id):
        """ Update an entry given its unique identifier """
        entry = ControlledVocabulary.objects(id=id).get()
        entry.update(**api.payload)
        return {'message': "Update entry '{}'".format(entry.primary_name)}

    def delete(self, id):
        """ Delete an entry given its unique identifier

            query parameters:
            - complete: boolean: Delete entry instead of deprecate it (cannot be undone) (default False)
        """

        force_delete = request.args.get('complete', False)

        entry = ControlledVocabulary.objects(id=id).get()
        if not force_delete:
            entry.update(deprecate=True)
            return {'message': "Deprecate entry '{}'".format(entry.primary_name)}
        else:
            entry.delete()
            return {'message': "Delete entry {}".format(entry.primary_name)}

from flask import request
from flask_restplus import Namespace, Resource, fields

from ..model import Property


ns = Namespace('Properties', description='Property related operations')

property_model = ns.model('Property', {
    'id': fields.String(attribute='pk', description='The unique identifier of the entry'),
    'label': fields.String(description='A human readable description of the entry'),
    'primary_name': fields.String(description='The unique name of the entry (in snake_case)'),
    'level': fields.String(description='The level the property is associated with (e.g. Study, Sample, ...)'),
    'synonyms': fields.List(fields.String(description='Alternatives to the priamry name')),
    'description': fields.String(description='A detailed description of the intended use', default=''),
    'deprecate': fields.Boolean(default=False)
})


@ns.route('/')
class ApiProperties(Resource):

    @ns.marshal_with(property_model)
    def get(self):
        """ Fetch a list with all entries

            query parameters:
            - deprecate: boolean: Indicate if deprecated entries should be returned as well (default False)
        """
        include_deprecate = request.args.get('deprecate', False)

        if not include_deprecate:
            entries = Property.objects(deprecate=False).all()
        else:
            # Include entries which are deprecated
            entries = Property.objects().all()

        return list(entries)

    @ns.expect(property_model)
    def post(self):
        """ Add a new entry """
        entry = Property(**ns.payload)
        entry.save()
        return {"message": "Add entry '{}'".format(entry.primary_name)}, 201


@ns.route('/id/<id>')
@ns.param('id', 'The property identifier')
class ApiProperty(Resource):

    @ns.marshal_with(property_model)
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        return Property.objects(id=id).get()

    @ns.expect(property_model)
    def put(self, id):
        """ Update entry given its unique identifier """
        entry = Property.objects(id=id).first()
        entry.update(**ns.payload)
        return {'message': "Update entry '{}'".format(entry.primary_name)}

    def delete(self, id):
        """ Deprecates an entry given its unique identifier

            query parameters:
            - complete: boolean: Delete entry instead of deprecate it (cannot be undone) (default False)
        """

        force_delete = request.args.get('complete', False)

        entry = Property.objects(id=id).get()
        if not force_delete:
            entry.update(deprecate=True)
            return {'message': "Deprecate entry '{}'".format(entry.primary_name)}
        else:
            entry.delete()
            return {'message': "Delete entry '{}'".format(entry.primary_name)}

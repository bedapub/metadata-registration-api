from flask_restplus import Namespace, Resource, fields
from mongoengine.errors import NotUniqueError

from ..model import Property


api = Namespace('Properties', description='Property related operations')

property_model = api.model('Property', {
    'id': fields.String(attribute='pk', description='The unique identifier of the entry'),
    'label': fields.String(description='A human readable description of the entry'),
    'primary_name': fields.String(description='The unique name of the entry (in snake_case)'),
    'level': fields.String(description='The level the property is associated with (e.g. Study, Sample, ...)'),
    'synonyms': fields.List(fields.String(description='Alternatives to the priamry name')),
    'description': fields.String(description='A detailed description of the intended use', default=''),
    'deprecate': fields.Boolean(default=False)
})


@api.route('/')
class ApiProperties(Resource):
    @api.marshal_with(property_model)
    def get(self):
        """ Fetch a list with all entries """
        entries = Property.objects().all()
        return list(entries)

    @api.expect(property_model)
    def post(self):
        """ Add a new entry """
        entry = Property(**api.payload)
        try:
            entry.save()
            return {'message': 'Add entry with name {}'.format(entry.primary_name)}, 201
        except NotUniqueError:
            return {'message': "Entry with name '{} 'Property already exists".format(entry.primary_name)}
        except:
            return {'message': "Error occurred"}


@api.route('/id/<id>')
@api.param('id', 'The property identifier')
class ApiProperty(Resource):
    @api.marshal_with(property_model, envelope='properties')
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        return Property.objects(id=id).first()

    @api.expect(property_model)
    def put(self, id):
        """ Update an entry given its unique identifier """
        entry = Property.objects(id=id).first()
        entry.update(**api.payload)
        return {'message': "Update entry '{}'".format(entry.primary_name)}

    def delete(self, id):
        """ Delete an entry given its unique identifier """
        try:
            entry = Property.objects(id=id).first()
            entry.delete()
            return {'message': "Delete entry with id '{}'".format(id)}
        except:
            return {'message': "Error occurred"}


@api.route('/name/<id>')
@api.param('name', 'The entry name')
class ApiProperty(Resource):
    @api.marshal_with(property_model)
    def get(self, name):
        """Fetch an entry given its unique name"""
        return Property.objects(name=name).first()

    @api.expect(property_model)
    def put(self, name):
        """ Update an entry given its unique name """
        try:
            p = Property.objects(primaryname=name).first()
            p.update(**api.payload)
            return {'message': "Updated entry '{}'".format(p.primary_name)}
        except:
            return {'message': "Error occurred"}

    def delete(self, name):
        """ Delete an entry given its unique name """
        try:
            entry = Property.objects(primary_name=name).first()
            entry.delete()
            return {'message': "Delete entry with id {}".format(id)}
        except:
            return {'message': "Error occurred"}


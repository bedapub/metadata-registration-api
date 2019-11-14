from flask_restplus import Namespace, Resource, fields
from mongoengine.errors import NotUniqueError

from ..model import ControlledVocabulary


api = Namespace('Controlled Vocabulary', description='Controlled vocabulary related operations')


property_model = api.model('Controlled Vocabulary', {
    'id': fields.String(attribute='pk', description='The unique identifier of the entry'),
    'label': fields.String(description='A human readable description of the entry'),
    'primary_name': fields.String(description='The name of the entry (in snake_case)'),
    'synonyms': fields.List(fields.String(description='Alternatives to the primary name')),
    'description': fields.String(description='A detailed description of the intended use', default=''),
    'deprecate': fields.Boolean(description="Indicator, if the entry is no longer used.", default=False)
})


@api.route('/')
class ApiControlledVocabulary(Resource):
    @api.marshal_with(property_model)
    def get(self):
        """ Fetch a list with all entries """
        res = ControlledVocabulary.objects().all()
        return list(res)

    @api.expect(property_model)
    def post(self):
        """ Add a new entry """
        p = ControlledVocabulary(**api.payload)
        try:
            p.save()
            return {'message': 'Added property with name {}'.format(p.primary_name)}, 201
        except NotUniqueError:
            return {'message': 'Property already exists'}


@api.route('/id/<id>')
@api.param('id', 'The property identifier')
class ApiControlledVocabulary(Resource):
    @api.marshal_with(property_model)
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        return ControlledVocabulary.objects(id=id).first()

    @api.expect(property_model)
    def put(self, id):
        """ Update an entry given its unique identifier """
        p = ControlledVocabulary.objects(id=id).first()
        p.update(**api.payload)
        return {'message': "Successfully updated {}".format(p.primary_name)}

    def delete(self, id):
        """ Delete an entry given its unique identifier """
        p = ControlledVocabulary.objects(id=id).first()
        p.delete()
        return {'message': "Delete entry with id {}".format(id)}


@api.route('/name/<id>')
@api.param('name', 'The property name')
class ApiControlledVocabulary(Resource):
    @api.marshal_with(property_model)
    def get(self, name):
        """Fetch an entry given its unique name"""
        return ControlledVocabulary.objects(primary_name=name).first()

    @api.expect(property_model)
    def put(self, name):
        """ Update an entry given its unique name """
        try:
            entry = ControlledVocabulary.objects(primary_name=name).first()
            entry.update(**api.payload)
            return {'message': "Successfully updated {}".format(entry.primary_name)}
        except:
            return {'message': "Error occurred"}

    def delete(self, name):
        """ Delete an entry given its unique name """
        try:
            entry = ControlledVocabulary.objects(primary_name=name).first()
            entry.delete()
            return {'message': "Delete entry with id {}".format(id)}
        except:
            return {'message': "Error occurred"}

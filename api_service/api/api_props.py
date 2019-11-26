from flask import request
from flask_restplus import Namespace, Resource, fields

from api_service.model import Property


api = Namespace('Properties', description='Property related operations')

entry_model = api.model('Property', {
    'label': fields.String(description='A human readable description of the entry'),
    'primary_name': fields.String(description='The unique name of the entry (in snake_case)'),
    'level': fields.String(description='The level the property is associated with (e.g. Study, Sample, ...)'),
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
        include_deprecate = request.args.get('deprecate', False)

        if not include_deprecate:
            entries = Property.objects(deprecate=False).all()
        else:
            # Include entries which are deprecated
            entries = Property.objects().all()

        return list(entries)

    @api.expect(entry_model)
    def post(self):
        """ Add a new entry

            The primary_name has to be unique and is internally used as a variable name. The passed string is
            preprocessed before it is inserted into the database. Preprocessing: All characters are converted to
            lower case, the leading and trailing white spaces are removed, and intermediate white spaces are replaced
            with underscores ("_").

            Do not pass a unique identifier since it is generated internally.

            synonyms (optional)

            deprecate (default=False)


        """
        entry = Property(**api.payload)
        entry.save()
        return {"message": "Add entry '{}'".format(entry.primary_name)}, 201


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
        return {'message': "Update entry '{}'".format(entry.primary_name)}

    @api.doc(params={'complete': "Boolean indicator to remove an entry instead of deprecating it (cannot be undone) "
                                 "(default False)"})
    def delete(self, id):
        """ Deprecates an entry given its unique identifier """
        force_delete = request.args.get('complete', False)

        entry = Property.objects(id=id).get()
        # see issue https://github.com/noirbizarre/flask-restplus/issues/199
        if not force_delete or (isinstance(force_delete, str) and force_delete.lower() == 'false'):
            entry.update(deprecate=True)
            return {'message': "Deprecate entry '{}'".format(entry.primary_name)}
        else:
            entry.delete()
            return {'message': "Delete entry '{}'".format(entry.primary_name)}

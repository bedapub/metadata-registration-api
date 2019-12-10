from flask_restplus import Namespace, Resource, fields
from flask_restplus import reqparse, inputs

from api_service.model import Study
from api_service.api.api_props import property_model_id

api = Namespace('Study', description='Study related operations')


field_model = api.model("Field", {
    "label": fields.String(),
    "property": fields.Nested(property_model_id),
    "value": fields.Raw()
})

status_model = api.model("Status", {
    "name": fields.String()
})

study_model = api.model("Study", {
    'fields': fields.List(fields.Nested(field_model)),
    'status': fields.Nested(status_model)
})

study_model_id = api.inherit("Study with id", study_model, {
    "id": fields.String()
})

# ----------------------------------------------------------------------------------------------------------------------

field_add_model = api.model("Add Field", {
    "label": fields.String(),
    "property": fields.String(),
    "value": fields.Raw()
})

study_add_model = api.model("Add Study", {
    "fields": fields.List(fields.Nested(field_add_model)),
    "status": fields.Nested(status_model)
})


@api.route('/')
class ApiForm(Resource):
    @api.marshal_with(study_model_id)
    @api.doc(params={'deprecated': "Boolean indicator which determines if deprecated entries should be returned as "
                                   "well  (default False)"})
    def get(self):
        """ Fetch a list with all entries """
        # Convert query parameters
        parser = reqparse.RequestParser()
        parser.add_argument('deprecated', type=inputs.boolean, location="args", default=False)
        args = parser.parse_args()

        include_deprecate = args['deprecated']

        if not include_deprecate:
            res = Study.objects(deprecated=False).all()
        else:
            # Include entries which are deprecated
            res = Study.objects().all()
        return list(res)

    @api.expect(study_add_model)
    def post(self):
        """ Add a new entry """
        p = Study(**api.payload)
        p.save()
        return {"message": "Add entry '{}'".format(p.name)}, 201


@api.route('/id/<id>')
@api.param('id', 'The property identifier')
class ApiForm(Resource):
    @api.marshal_with(study_model_id)
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        return Study.objects(id=id).get()

    @api.expect(study_add_model)
    def put(self, id):
        """ Update an entry given its unique identifier """
        entry = Study.objects(id=id).get()
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

        entry = Study.objects(id=id).get()
        if not force_delete:
            entry.update(deprecated=True)
            return {'message': "Deprecate entry '{}'".format(entry.name)}
        else:
            entry.delete()
            return {'message': "Delete entry {}".format(entry.name)}

@api.route("/<id>/field")
class ApiField(Resource):

    @api.marshal_with(field_model)
    def get(self, id):
        entries = Study.objects(id=id).fields.objects().all()
        return list(entries)
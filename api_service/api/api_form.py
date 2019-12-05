from flask_restplus import Namespace, Resource, fields, marshal_with
from flask_restplus import reqparse, inputs

from api_service.model import Form
from api_service.api.api_props import property_model_id


api = Namespace('Form', description='Form related operations')

field_meta_model = api.model("Field Metadata", {
    "class_name": fields.String(),
})

field_add_model = api.model("Add Field", {
    'label': fields.String(),
    'property': fields.String(),
    'description': fields.String(),
    'metadata': fields.Nested(field_meta_model),
    'args': fields.List(fields.Raw()),
    'kwargs': fields.List(fields.Raw())
})

form_add_model = api.model("Add Form", {
    'label': fields.String(description='Human readable name of the entry'),
    'name': fields.String(description='Internal representation of the entry (in snake_case)'),
    'description': fields.String(description='Detailed description of the intended use', default=''),
    'fields': fields.List(fields.Nested(field_add_model)),
    'deprecate': fields.Boolean(description="Indicator, if the entry is no longer used.", default=False)
})


field_model = api.model("Field", {
    # 'name': fields.String(attribute='property_model_id.name'),
    'label': fields.String(),
    'property': fields.Nested(property_model_id),
    'description': fields.String(),
    'metadata': fields.Nested(field_meta_model),
    'args': fields.List(fields.Raw()),
    'kwargs': fields.List(fields.Raw()),
})


form_model = api.model("Form", {
    'label': fields.String(description='Human readable name of the entry'),
    'name': fields.String(description='Internal representation of the entry (in snake_case)'),
    'description': fields.String(description='Detailed description of the intended use', default=''),
    'fields': fields.List(fields.Nested(field_model)),
    'deprecate': fields.Boolean(description="Indicator, if the entry is no longer used.", default=False)
})

form_model_id = api.inherit("Form with id", form_model, {
    'id': fields.String(attribute='pk', description='Unique identifier of the entry'),
})


@api.route('/')
class ApiForm(Resource):
    @marshal_with(form_model_id)
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
            res = Form.objects(deprecate=False).all()
        else:
            # Include entries which are deprecated
            res = Form.objects().all()
        return list(res)

    @api.expect(form_add_model)
    def post(self):
        """ Add a new entry """
        p = Form(**api.payload)
        p.save()
        return {"message": "Add entry '{}'".format(p.name)}, 201


@api.route('/id/<id>')
@api.param('id', 'The property identifier')
class ApiForm(Resource):
    @marshal_with(form_model_id)
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        return Form.objects(id=id).get()

    @api.expect(form_model)
    def put(self, id):
        """ Update an entry given its unique identifier """
        entry = Form.objects(id=id).get()
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

        entry = Form.objects(id=id).get()
        if not force_delete:
            entry.update(deprecate=True)
            return {'message': "Deprecate entry '{}'".format(entry.name)}
        else:
            entry.delete()
            return {'message': "Delete entry {}".format(entry.name)}

@api.route("/<id>/field")
class ApiField(Resource):

    @marshal_with(field_model)
    def get(self, id):
        entries = Form.objects(id=id).fields.objects().all()
        return list(entries)
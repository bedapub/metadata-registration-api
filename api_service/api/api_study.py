from flask_restplus import Namespace, Resource, fields
from flask_restplus import reqparse, inputs

from api_service.model import Study
from api_service.api.api_props import property_model_id
from api_service.api.decorators import token_required

api = Namespace('Studies', description='Study related operations')

# Model definition
# ----------------------------------------------------------------------------------------------------------------------

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

field_add_model = api.model("Add Field", {
    "label": fields.String(),
    "property": fields.String(),
    "value": fields.Raw()
})

study_add_model = api.model("Add Study", {
    "fields": fields.List(fields.Nested(field_add_model)),
    "status": fields.Nested(status_model)
})


# Routes
# ----------------------------------------------------------------------------------------------------------------------

@api.route('/')
class ApiStudy(Resource):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('deprecated',
                            type=inputs.boolean,
                            location="args",
                            default=False,
                            help="Boolean indicator which determines if deprecated entries should be returned as well",
                            )

    # @token_required
    @api.marshal_with(study_model_id)
    @api.expect(parser=get_parser)
    def get(self):
        """ Fetch a list with all entries """
        # Convert query parameters
        args = self.get_parser.parse_args()
        include_deprecate = args['deprecated']

        if not include_deprecate:
            res = Study.objects(deprecated=False).all()
        else:
            # Include entries which are deprecated
            res = Study.objects().all()
        return list(res)

    @token_required
    @api.expect(study_add_model)
    def post(self):
        """ Add a new entry """
        entry = Study(**api.payload)
        entry.save()
        return {"message": f"Add entry '{entry.name}'"}, 201


@api.route('/id/<id>')
@api.route('/id/<id>/')
@api.param('id', 'The property identifier')
class ApiStudy(Resource):
    _delete_parser = reqparse.RequestParser()
    _delete_parser.add_argument('complete',
                               type=inputs.boolean,
                               default=False,
                               help="Boolean indicator to remove an entry instead of deprecating it (cannot be undone)"
                               )

    # @token_required
    @api.marshal_with(study_model_id)
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        return Study.objects(id=id).get()

    @token_required
    @api.expect(study_add_model)
    def put(self, user, id):
        """ Update an entry given its unique identifier """
        entry = Study.objects(id=id).get()
        entry.update(**api.payload)
        return {'message': f"Update entry '{entry.name}'"}

    @token_required
    @api.expect(parser=_delete_parser)
    def delete(self, user, id):
        """ Delete an entry given its unique identifier """
        args = self._delete_parser.parse_args()
        force_delete = args['complete']

        entry = Study.objects(id=id).get()
        if not force_delete:
            entry.update(deprecated=True)
            return {'message': f"Deprecate entry '{entry.name}'"}
        else:
            entry.delete()
            return {'message': f"Delete entry {entry.name}"}

from flask_restplus import Namespace, Resource, fields
from flask_restplus import reqparse, inputs

from api_service.model import ControlledVocabulary
from api_service.api.decorators import token_required


api = Namespace('Controlled Vocabulary', description='Controlled vocabulary related operations')

# ----------------------------------------------------------------------------------------------------------------------

cv_item_model = api.model("CV item", {
    'label': fields.String(description='Human readable name of the entry'),
    'name': fields.String(description='Internal representation of the entry (in snake_case)'),
    'description': fields.String(description="Detailed explanation of the intended use"),
    'synonyms': fields.List(fields.String())
})

ctrl_voc_model = api.model('Controlled Vocabulary', {
    'label': fields.String(description='Human readable name of the entry'),
    'name': fields.String(description='Internal representation of the entry (in snake_case)'),
    'description': fields.String(description='Detailed description of the intended use', default=''),
    'items': fields.List(fields.Nested(cv_item_model)),
    'deprecated': fields.Boolean(description="Indicator, if the entry is no longer used.", default=False)
})

ctrl_voc_model_id = api.inherit("Controlled Vocabulary with id", ctrl_voc_model, {
    'id': fields.String(attribute='pk', description='Unique identifier of the entry'),
})

post_response_model = api.model("Post response", {
    'message': fields.String(),
    'id': fields.String(description="Id of inserted entry")
})

# ----------------------------------------------------------------------------------------------------------------------

@api.route('/')
class ApiControlledVocabulary(Resource):

    get_parser = reqparse.RequestParser()
    get_parser.add_argument('deprecated',
                            type=inputs.boolean,
                            location="args",
                            default=False,
                            help="Boolean indicator which determines if deprecated entries should be returned as well",
                            )

    @api.marshal_with(ctrl_voc_model_id)
    @api.expect(parser=get_parser)
    def get(self):
        """ Fetch a list with all entries """

        # Convert query parameters
        args = self.get_parser.parse_args()
        include_deprecate = args['deprecated']

        if not include_deprecate:
            # Select only active entries
            res = ControlledVocabulary.objects(deprecated=False).all()
        else:
            # Include deprecated entries
            res = ControlledVocabulary.objects().all()
        return list(res)

    @token_required
    @api.expect(ctrl_voc_model)
    @api.response(201, "Success", post_response_model)
    def post(self, user):
        """ Add a new entry """
        p = ControlledVocabulary(**api.payload)
        p = p.save()
        return {"message": "Add entry '{}'".format(p.name),
                "id": str(p.id)}, 201


@api.route('/id/<id>')
@api.param('id', 'The property identifier')
class ApiControlledVocabulary(Resource):

    delete_parser = reqparse.RequestParser()
    delete_parser.add_argument('complete',
                               type=inputs.boolean,
                               default=False,
                               help="Boolean indicator to remove an entry instead of deprecating it (cannot be undone)"
                               )

    @api.marshal_with(ctrl_voc_model_id)
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        return ControlledVocabulary.objects(id=id).get()

    @token_required
    @api.expect(ctrl_voc_model)
    def put(self, user, id):
        """ Update an entry given its unique identifier """
        entry = ControlledVocabulary.objects(id=id).get()
        entry.update(**api.payload)
        return {'message': "Update entry '{}'".format(entry.name)}

    @token_required
    @api.expect(parser=delete_parser)
    def delete(self, user, id):
        """ Delete an entry given its unique identifier """

        args = self.delete_parser.parse_args()

        force_delete = args['complete']

        entry = ControlledVocabulary.objects(id=id).get()
        if not force_delete:
            entry.update(deprecated=True)
            return {'message': "Deprecate entry '{}'".format(entry.name)}
        else:
            entry.delete()
            return {'message': "Delete entry {}".format(entry.name)}

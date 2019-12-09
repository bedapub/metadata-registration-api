from flask_restplus import Namespace, Resource, fields
from flask_restplus import reqparse, inputs

from api_service.model import User


api = Namespace('User', description='User related operations')

user_model = api.model("User", {
    "firstname": fields.String(),
    "lastname": fields.String(),
    "email": fields.String(),
    "password": fields.String(),
    "is_active": fields.Boolean()
})

user_model_id = api.inherit("User with id", user_model, {
    'id': fields.String(attribute='pk', description='Unique identifier of the entry'),
})

post_response_model = api.model("Post response", {
    'message': fields.String(),
    'id': fields.String(description="Id of inserted entry")
})


@api.route('/')
class ApiControlledVocabulary(Resource):
    @api.marshal_with(user_model_id)
    @api.doc(params={'deactivated': "Boolean indicator which determines if deactivated users should be returned as "
                                    "well  (default False)"})
    def get(self):
        """ Fetch a list with all entries """

        # Convert query parameters
        parser = reqparse.RequestParser()
        parser.add_argument('deactivated', type=inputs.boolean, location="args", default=False)
        args = parser.parse_args()

        include_deactivated = args['deactivated']

        if not include_deactivated:
            # Select only active entries
            res = User.objects(is_active=True).all()
        else:
            # Include deprecated entries
            res = User.objects().all()
        return list(res)

    @api.expect(user_model)
    @api.response(201, "Success", post_response_model)
    def post(self):
        """ Add a new entry """
        p = User(**api.payload)
        p = p.save()
        return {"message": "Add entry '{}'".format(p.name),
                "id": str(p.id)}, 201


@api.route('/id/<id>')
@api.param('id', 'The property identifier')
class ApiControlledVocabulary(Resource):
    @api.marshal_with(user_model_id)
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        return User.objects(id=id).get()

    @api.expect(user_model)
    def put(self, id):
        """ Update an entry given its unique identifier """
        entry = User.objects(id=id).get()
        entry.update(**api.payload)
        return {'message': "Update entry '{}'".format(entry.name)}

    @api.doc(params={'complete': "Boolean indicator to remove an entry instead of inactivating it (cannot be undone) "
                                 "(default False)"})
    def delete(self, id):
        """ Delete an entry given its unique identifier """

        parser = reqparse.RequestParser()
        parser.add_argument('complete', type=inputs.boolean, default=False)
        args = parser.parse_args()

        force_delete = args['complete']

        entry = User.objects(id=id).get()
        if not force_delete:
            entry.update(is_active=False)
            return {'message': "Inactivated entry '{}'".format(entry.name)}
        else:
            entry.delete()
            return {'message': "Delete entry {}".format(entry.name)}

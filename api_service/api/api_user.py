import datetime
import jwt

from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app as app

from flask_restplus import Namespace, Resource, fields
from flask_restplus import reqparse, inputs

from api_service.api.decorators import token_required, TokenException
from api_service.model import User

api = Namespace('User', description='User related operations')

# ----------------------------------------------------------------------------------------------------------------------

user_model = api.model("User", {
    "firstname": fields.String(),
    "lastname": fields.String(),
    "email": fields.String(),
    "password": fields.String(),
    "is_active": fields.Boolean(default=True)
})

user_model_id = api.inherit("User with id", user_model, {
    'id': fields.String(attribute='pk', description='Unique identifier of the entry'),
})

post_response_model = api.model("Post response", {
    'message': fields.String(),
    'id': fields.String(description="Id of inserted entry")
})

login_model = api.model("Login", {
    "email": fields.String(required=True),
    "password": fields.String(required=True)
})


# ----------------------------------------------------------------------------------------------------------------------

@api.route("/login")
class Login(Resource):

    @api.expect(login_model)
    def post(self):
        """ Fetch an access token to perform requests which require elevated privileges

        Upon successful login, you receive an access token. Pass the token as value of 'x-access-token' in
        the header of every request that requires elevated privileges. The token is only valid for a certain time
        interval.
        """

        email = api.payload['email']
        password = api.payload['password']

        user = User.objects(email=email).first()

        if not user or not check_password_hash(user.password, password):
            raise Exception("The email does not exists or the email password combination is wrong")

        # Create token
        token = jwt.encode({'user_id': str(user.id),
                            'iat': datetime.datetime.utcnow(),
                            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},
                           app.secret_key)

        return {'x-access-token': token.decode("UTF-8")}


@api.route('/')
class ApiUser(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('deactivated',
                        type=inputs.boolean,
                        location="args",
                        default=False,
                        help="Boolean indicator which determines if deactivated users should be returned as well.",
                        )

    # @token_required
    @api.expect(parser=parser)
    @api.marshal_with(user_model_id)
    def get(self):
        """ Fetch a list with all entries """
        args = self.parser.parse_args()

        include_deactivated = args['deactivated']

        if not include_deactivated:
            # Select only active entries
            res = User.objects(is_active=True).all()
        else:
            # Include deprecated entries
            res = User.objects().all()
        return list(res)

    @token_required
    @api.expect(user_model)
    @api.response(201, "Success", post_response_model)
    def post(self, user):
        """ Add a new entry """
        p = User(**api.payload)
        p = p.save()
        return {"message": "Add user '{}'".format(p.firstname),
                "id": str(p.id)}, 201


@api.route('/id/<id>')
@api.param('id', 'The property identifier')
class ApiUser(Resource):
    delete_parser = reqparse.RequestParser()
    delete_parser.add_argument('complete',
                               type=inputs.boolean,
                               default=False,
                               help="Boolean indicator to remove an entry instead of inactivating it (cannot be "
                                    "undone).",
                               )

    # @token_required
    @api.marshal_with(user_model_id)
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        return User.objects(id=id).get()

    @token_required
    @api.expect(user_model)
    def put(self, user, id):
        """ Update an entry given its unique identifier """
        entry = User.objects(id=id).get()
        entry.update(**api.payload)
        return {'message': "Update entry '{}'".format(entry.firstname)}

    @token_required
    @api.expect(parser=delete_parser)
    def delete(self, user, id):
        """ Delete an entry given its unique identifier """

        args = self.delete_parser.parse_args()
        force_delete = args['complete']

        entry = User.objects(id=id).get()
        if not force_delete:
            entry.update(is_active=False)
            return {'message': "Inactivated entry '{}'".format(entry.firstname)}
        else:
            entry.delete()
            return {'message': "Delete entry {}".format(entry.firstname)}
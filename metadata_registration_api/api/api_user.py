import datetime
import jwt

from werkzeug.security import check_password_hash
from flask import current_app as app

from flask_restx import Namespace, Resource, fields
from flask_restx import reqparse, inputs

from metadata_registration_api.api.decorators import token_required
from metadata_registration_api.model import User

api = Namespace("Users", description="User related operations")

# ----------------------------------------------------------------------------------------------------------------------

user_model = api.model("User", {
    "firstname": fields.String(),
    "lastname": fields.String(),
    "email": fields.String(),
    "password": fields.String(),
    "is_active": fields.Boolean(default=True)
})

user_model_id = api.inherit("User with id", user_model, {
    "id": fields.String(attribute="pk", description="Unique identifier of the entry"),
})

post_response_model = api.model("Post response", {
    "message": fields.String(),
    "id": fields.String(description="Id of inserted entry")
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

        email = api.payload["email"]
        password = api.payload["password"]

        user = User.objects(email=email).first()

        if not user or not check_password_hash(user.password, password):
            raise Exception("The email does not exists or the email password combination is wrong")

        # Create token
        token = jwt.encode({"user_id": str(user.id),
                            "iat": datetime.datetime.utcnow(),
                            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},
                           app.secret_key)

        return {"X-Access-Token": token.decode("UTF-8")}


@api.route("")
class ApiUser(Resource):
    _delete_parser = reqparse.RequestParser()
    _delete_parser.add_argument("complete",
                                type=inputs.boolean,
                                default=False,
                                help="Boolean indicator to remove an entry instead of deprecating it (cannot be undone)"
                                )

    parser = reqparse.RequestParser()
    parser.add_argument("deactivated",
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

        include_deactivated = args["deactivated"]

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
    def post(self, user=None):
        """ Add a new entry """
        entry = User(**api.payload)
        entry = entry.save()
        return {"message": f"Add user '{entry.firstname}'",
                "id": str(entry.id)}, 201

    @token_required
    @api.expect(parser=_delete_parser)
    def delete(self, user=None):
        """ Delete all entries"""

        args = self._delete_parser.parse_args()

        force_delete = args["complete"]

        entry = User.objects().all()
        if not force_delete:
            entry.update(deprecated=True)
            return {"message": "Deprecate all entries"}
        else:
            entry.delete()
            return {"message": "Delete all entries"}


@api.route("/id/<id>", strict_slashes=False)
@api.param("id", "The property identifier")
class ApiUser(Resource):
    _delete_parser = reqparse.RequestParser()
    _delete_parser.add_argument("complete",
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
    def put(self, id, user=None):
        """ Update an entry given its unique identifier """
        entry = User.objects(id=id).get()
        entry.update(**api.payload)
        return {"message": f"Update entry '{entry.firstname}'"}

    @token_required
    @api.expect(parser=_delete_parser)
    def delete(self, id, user=None):
        """ Delete an entry given its unique identifier """

        args = self._delete_parser.parse_args()
        force_delete = args["complete"]

        entry = User.objects(id=id).get()
        if not force_delete:
            entry.update(is_active=False)
            return {"message": f"Inactivated entry '{entry.firstname}'"}
        else:
            entry.delete()
            return {"message": f"Delete entry {entry.firstname}"}

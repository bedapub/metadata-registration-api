from functools import wraps
import jwt
from jwt.exceptions import InvalidSignatureError

from flask import current_app as app, request

from . import api
from database_model.model import User


class TokenException(Exception):
    pass


def token_required(f):
    """ A decorator to ensure that the request contains an access token"""

    # Add security documentation to swagger
    f = api.doc(security="apikey")(f)

    @wraps(f)
    def decorated(self, *args, **kwargs):
        """ Get token and try to decode it"""

        if not app.config['CHECK_ACCESS_TOKEN']:
            user = type("DummyUser", (), {"id": "dummy_id"})()
            return f(self, user, *args, **kwargs)

        token = request.headers.get("x-access-token")

        if not token:
            raise TokenException(f"Your '{f.__name__}' request on '{request.path}' requires an access token. "
                                 f"Please provide an 'x-access-token' in the header of the request. A token will be "
                                 f"generated through log in.")
        try:
            payload = jwt.decode(token, app.secret_key)
        except InvalidSignatureError:
            raise TokenException(f"Your given token is invalid. Your can receive a token through log in.")

        # Get the user and pass it to the request
        user = User.objects(id=payload['user_id']).first()

        return f(self, user, *args, **kwargs)
    return decorated

from functools import wraps
import logging
import jwt
from jwt.exceptions import InvalidSignatureError

from flask import current_app as app, request

from . import api
from metadata_registration_api.model import User

logger = logging.getLogger(__name__)


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
            return f(self, *args, **kwargs)

        token = request.headers.get("X-Access-Token")

        if not token:
            logger.info(f"No access token provided for protected endpoint {request.path}.")
            raise TokenException(f"Your '{f.__name__}' request on '{request.path}' requires an access token. "
                                 f"Please provide an 'x-access-token' in the header of the request. A token will be "
                                 f"generated through log in.")
        try:
            payload = jwt.decode(token, app.secret_key)
        except InvalidSignatureError:
            raise TokenException(f"Your given token is invalid. Your can receive a token through log in.")

        # Get the user and pass it to the request
        user = User.objects(id=payload['user_id']).first()

        return f(self, user=user, *args, **kwargs)
    return decorated

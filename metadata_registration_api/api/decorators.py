from functools import wraps
import logging
import jwt
from jwt import DecodeError
from jwt.exceptions import InvalidSignatureError

from flask import current_app as app, request

from metadata_registration_api.api import api
from metadata_registration_api.model import User
from metadata_registration_api.errors import TokenException

logger = logging.getLogger(__name__)




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
        except InvalidSignatureError and DecodeError as e:
            raise TokenException(f"Your given token is invalid. Your can receive a valid token bt login.") from e

        # Get the user and pass it to the request
        user = User.objects(id=payload['user_id']).first()

        return f(self, user=user, *args, **kwargs)
    return decorated

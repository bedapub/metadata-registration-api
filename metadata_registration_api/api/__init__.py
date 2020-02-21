import os

from flask_restx import Api
from flask import current_app as app

from mongoengine.errors import NotUniqueError, ValidationError, DoesNotExist

authorizations = {
    "apikey": {
        "type": "apiKey",
        "in": "header",
        "name": "x-access-token"
    }
}

api = Api(version="0.5.1", authorizations=authorizations)

# noinspection PyPep8
from .api_props import api as ns_1
# noinspection PyPep8
from .api_ctrl_voc import api as ns_2
# noinspection PyPep8
from .api_form import api as ns_3
# noinspection PyPep8
from .api_study import api as ns_4
# noinspection PyPep8
from .api_user import api as ns_5

api.add_namespace(ns_1, path=os.environ.get("API_EP_PROPERTY", "/properties"))
api.add_namespace(ns_2, path=os.environ.get("API_EP_CTRL_VOC", "/ctrl_voc"))
api.add_namespace(ns_3, path=os.environ.get("API_EP_FORM", "/forms"))
api.add_namespace(ns_4, path=os.environ.get("API_EP_STUDY", "/studies"))
api.add_namespace(ns_5, path=os.environ.get("API_EP_USER", '/users'))


@api.errorhandler(ValidationError)
def handle_validation_error(error):
    return {"message": f"Validation error: {error.message}"}, 400


@api.errorhandler(NotUniqueError)
def handle_not_unique_error(error):
    return {"message": f"The entry already exists. {error}"}, 409


@api.errorhandler(DoesNotExist)
def handle_does_not_exist_error(error):
    return {"message": f"The entry does not exist. {error}"}, 404


@api.errorhandler(Exception)
def general_error_handler(error):
    return {
               "error type": str(error.__class__.__name__),
               "message": f"{error}"}, 404

import os
import io
import re

from flask_restx import Api

from mongoengine.errors import NotUniqueError, DoesNotExist
from dynamic_form.errors import DynamicFormException
from study_state_machine.errors import StateMachineException

from metadata_registration_api.errors import TokenException, IdenticalPropertyException, RequestBodyException

authorizations = {
    "apikey": {
        "type": "apiKey",
        "in": "header",
        "name": "x-access-token"
    }
}

current_file_path = os.path.dirname(__file__)
relative_path = "../__init__.py"
init_file = os.path.join(current_file_path, relative_path)

with io.open(init_file, "rt", encoding="utf8") as f:
    version = re.search(r"__version__ = \"(.*?)\"", f.read()).group(1)

api = Api(version=version, authorizations=authorizations)

# noinspection PyPep8
from .api_props import api as ns_1
# noinspection PyPep8
from .api_ctrl_voc import api as ns_2
# noinspection PyPep8
from .api_form import api as ns_3
# noinspection PyPep8
from .api_study import api as ns_4
# noinspection PyPep8
from .api_study_export import api as ns_4_export
# noinspection PyPep8
from .api_user import api as ns_5

api.add_namespace(ns_1, path=os.environ.get("API_EP_PROPERTY", "/properties"))
api.add_namespace(ns_2, path=os.environ.get("API_EP_CTRL_VOC", "/ctrl_voc"))
api.add_namespace(ns_3, path=os.environ.get("API_EP_FORM", "/forms"))
api.add_namespace(ns_4, path=os.environ.get("API_EP_STUDY", "/studies"))
api.add_namespace(ns_4_export, path=os.environ.get("API_EP_STUDY", "/studies"))
api.add_namespace(ns_5, path=os.environ.get("API_EP_USER", '/users'))


@api.errorhandler(TokenException)
def handle_authorization_error(error):
    return {
               "error type": str(error.__class__.__name__),
               "message": str(error)
           }, 401


@api.errorhandler(DynamicFormException)
@api.errorhandler(StateMachineException)
@api.errorhandler(RequestBodyException)
@api.errorhandler(IdenticalPropertyException)
def state_machine_exception(error):
    return {
        "error_type": str(error.__class__.__name__),
        "message": str(error)
    }, 422


@api.errorhandler(NotUniqueError)
def handle_not_unique_error(error):
    return {
               "error_type": str(error.__class__.__name__),
               "message": f"The entry already exists: {str(error)}"
           }, 409


@api.errorhandler(DoesNotExist)
def handle_does_not_exist_error(error):
    return {
               "error_type": str(error.__class__.__name__),
               "message": f"The entry does not exist: {str(error)}"
           }, 404


@api.errorhandler(Exception)
def general_error_handler(error):
    return {
               "error type": str(error.__class__.__name__),
               "message": f"{error}"}, 404

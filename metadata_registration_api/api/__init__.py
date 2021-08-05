import os
import io
import re

from flask_restx import Api

from mongoengine.errors import NotUniqueError, DoesNotExist
from dynamic_form.errors import DynamicFormException
from study_state_machine.errors import StateMachineException

from metadata_registration_api.errors import (
    TokenException,
    IdenticalPropertyException,
    RequestBodyException,
)

authorizations = {
    "apikey": {"type": "apiKey", "in": "header", "name": "x-access-token"}
}

current_file_path = os.path.dirname(__file__)
relative_path = "../__init__.py"
init_file = os.path.join(current_file_path, relative_path)

with io.open(init_file, "rt", encoding="utf8") as f:
    version = re.search(r"__version__ = \"(.*?)\"", f.read()).group(1)

api = Api(version=version, authorizations=authorizations)

from . import api_props
from . import api_ctrl_voc
from . import api_form
from . import api_study
from . import api_study_dataset
from . import api_study_sample
from . import api_study_export
from . import api_user
from . import api_state

api.add_namespace(api_props.api, path=os.environ.get("API_EP_PROPERTY", "/properties"))
api.add_namespace(api_ctrl_voc.api, path=os.environ.get("API_EP_CTRL_VOC", "/ctrl_voc"))
api.add_namespace(api_form.api, path=os.environ.get("API_EP_FORM", "/forms"))
api.add_namespace(api_study.api, path=os.environ.get("API_EP_STUDY", "/studies"))
api.add_namespace(
    api_study_dataset.api, path=os.environ.get("API_EP_STUDY", "/studies")
)
api.add_namespace(api_study_sample.api, path=os.environ.get("API_EP_STUDY", "/studies"))
api.add_namespace(api_study_export.api, path=os.environ.get("API_EP_STUDY", "/studies"))
api.add_namespace(api_user.api, path=os.environ.get("API_EP_USER", "/users"))
api.add_namespace(api_state.api, path=os.environ.get("API_EP_STATE", "/states"))


@api.errorhandler(TokenException)
def handle_authorization_error(error):
    return {"error type": str(error.__class__.__name__), "message": str(error)}, 401


@api.errorhandler(DynamicFormException)
@api.errorhandler(StateMachineException)
@api.errorhandler(RequestBodyException)
@api.errorhandler(IdenticalPropertyException)
def state_machine_exception(error):
    return {"error_type": str(error.__class__.__name__), "message": str(error)}, 422


@api.errorhandler(NotUniqueError)
def handle_not_unique_error(error):
    return {
        "error_type": str(error.__class__.__name__),
        "message": f"The entry already exists: {str(error)}",
    }, 409


@api.errorhandler(DoesNotExist)
def handle_does_not_exist_error(error):
    return {
        "error_type": str(error.__class__.__name__),
        "message": f"The entry does not exist: {str(error)}",
    }, 404


@api.errorhandler(Exception)
def general_error_handler(error):
    return {"error type": str(error.__class__.__name__), "message": f"{error}"}, 404

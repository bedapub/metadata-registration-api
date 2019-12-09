from flask_restplus import Api

from mongoengine.errors import NotUniqueError, ValidationError, DoesNotExist

from api_service.api.api_props import api as ns_1
from api_service.api.api_ctrl_voc import api as ns_2
from api_service.api.api_form import api as ns_3
from api_service.api.api_study import api as ns_4

api = Api(version="0.5.0")


api.add_namespace(ns_1, path='/properties')
api.add_namespace(ns_2, path='/ctrl_voc')
api.add_namespace(ns_3, path='/form')
api.add_namespace(ns_4, path='/study')


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
    return {"message": f"{error}"}, 404

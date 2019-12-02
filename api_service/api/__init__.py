from flask_restplus import Api

from mongoengine.errors import NotUniqueError, ValidationError

from .api_props import api as ns_1
from .api_ctrl_voc import api as ns_2

api = Api(title="Property and Controlled Vocabulary Service",
          version="0.3.1",
          description="An API to manage properties and controlled vocabularies. Contact: <rafael.mueller@roche.com>. "
                      "\n\n"
                      "The code is available here: https://github.roche.com/rafaelsm/ApiService. Any issue reports or "
                      "feature requests are appreciated."
          )


api.add_namespace(ns_1, path='/properties')
api.add_namespace(ns_2, path='/ctrl_voc')


@api.errorhandler(ValidationError)
def handle_validation_error(error):
    return {"message": error.message}, 404


@api.errorhandler(NotUniqueError)
def handle_not_unique_error(error):
    return {"message": "The entry already exists. {}".format(error)}, 404

@api.errorhandler(Exception)
def general_error_handler(error):
    return {"message" : f"{error}"}, 404

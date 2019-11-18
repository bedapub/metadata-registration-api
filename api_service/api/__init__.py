from flask_restplus import Api

from mongoengine.errors import NotUniqueError, ValidationError

from .api_props import ns as ns_1
from .api_ctrl_voc import api as ns_2

api = Api(title='Property and Controlled Vocabulary Service',
          version='0.2.0 beta',
          description='An API to manage properties and controlled vocabularies. Contact: <rafael.mueller@roche.com>',
          contact="rafael.mueller@roche.com")


api.add_namespace(ns_1, path='/properties')
api.add_namespace(ns_2, path='/ctrl_voc')


@api.errorhandler(ValidationError)
def handle_validation_error(error):
    return {"message": error.message}, 404


@api.errorhandler(NotUniqueError)
def handle_not_unique_error():
    return {"message": "Property already exists."}, 404

from flask_restplus import Api

from .api_props import api as ns_1
from .api_ctrl_voc import api as ns_2

api = Api(title='Property and Controlled Vocabulary Service',
          version='0.1.0 beta',
          description='An API to manage properties and controlled vocabularies. Contact: <rafael.mueller@roche.com>',
          contact="rafael.mueller@roche.com")

api.add_namespace(ns_1, path='/properties')
api.add_namespace(ns_2, path='/ctrl_voc')

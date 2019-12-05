import os

from flask import Flask
from mongoengine import connect

from api_service.my_utils import load_credentials


def config_app(app, credentials):

    app.debug = credentials['DEBUG']

    # Load app secret and convert to byte string
    app.secret_key = credentials['app_secret'].encode()

    # Load mongo database credentials
    app.config['MONGODB_DB'] = credentials['database']['mongodb']['database']
    app.config['MONGODB_HOST'] = credentials['database']['mongodb']['hostname']
    app.config['MONGODB_PORT'] = credentials['database']['mongodb']['port']
    app.config['MONGODB_USERNAME'] = credentials['database']['mongodb']['username']
    app.config['MONGODB_PASSWORD'] = credentials['database']['mongodb']['password']
    app.config['MONGODB_CONNECT'] = False

    # Load mongo collection names
    app.config['MONGODB_COL_PROPERTY'] = credentials['database']['mongodb']['collection']['property']
    app.config['MONGODB_COL_CTRL_VOC'] = credentials['database']['mongodb']['collection']['ctrl_voc']
    app.config['MONGODB_COL_FORM'] = credentials['database']['mongodb']['collection']['form']


def create_app(config='DEVELOPMENT'):
    app = Flask(__name__)

    cert_path = os.path.join(os.path.dirname(__file__), '..', '.credentials.yaml')
    credentials = load_credentials(path=cert_path)
    config_app(app, credentials[config])

    # Restplus API
    app.config['ERROR_404_HELP'] = False

    connect(app.config['MONGODB_DB'],
            host=app.config['MONGODB_HOST'],
            port=app.config['MONGODB_PORT'],
            username=app.config['MONGODB_USERNAME'],
            password=app.config['MONGODB_PASSWORD'],
            )

    from api_service.model import Property, ControlledVocabulary, Form
    Property._meta['collection'] = app.config['MONGODB_COL_PROPERTY']
    ControlledVocabulary._meta['collection'] = app.config['MONGODB_COL_CTRL_VOC']
    Form._meta['collection'] = app.config['MONGODB_COL_FORM']

    from api_service.api import api
    api.init_app(app,
                 title="Property and Controlled Vocabulary Service",
                 contact="Rafael Müller",
                 contact_email="rafael.mueller@roche.com",
                 description="An API to manage properties and controlled vocabularies."
                             "\n\n"
                             "The code is available here: https://github.roche.com/rafaelsm/ApiService. Any issue "
                             "reports or feature requests are appreciated.")

    return app


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(description="Start property microservice")
    parser.add_argument('--config', type=str,
                        default="DEVELOPMENT",
                        help="Mode in which the application should start")

    args = parser.parse_args()

    app = create_app(**vars(args))
    app.run(host='0.0.0.0', port=5001)

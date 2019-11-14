import os

from flask import Flask
from mongoengine import connect

from property_service.my_utils import load_credentials


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

    app.config['MONGODB_COL_PROPERTY'] = credentials['database']['mongodb']['collection']['property']
    app.config['MONGODB_COL_CTRL_VOC'] = credentials['database']['mongodb']['collection']['ctrl_voc']


def create_app(config='DEVELOPMENT'):
    app = Flask(__name__)

    cert_temp_path = os.path.join(os.path.dirname(__file__), 'templates')
    cert_path = os.path.join(os.path.dirname(__file__), '..', '.credentials.yaml')
    credentials = load_credentials(path=cert_path, template_location=cert_temp_path)
    config_app(app, credentials[config])

    connect(app.config['MONGODB_DB'],
            host=app.config['MONGODB_HOST'],
            port=app.config['MONGODB_PORT'],
            username=app.config['MONGODB_USERNAME'],
            password=app.config['MONGODB_PASSWORD'],
            )

    from property_service.model import Property
    Property._meta['collection'] = app.config['MONGODB_COL_PROPERTY']
    Property._meta['collection'] = app.config['MONGODB_COL_CTRL_VOC']

    from property_service.api import api
    api.init_app(app)

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

import os
import logging
import atexit

from flask import Flask
from mongoengine import connect

from metadata_registration_api.my_utils import load_credentials
from metadata_registration_api.datastore_api import ApiDataStore
from metadata_registration_api.api import api

from dynamic_form import FormManager
from state_machine import context

logger = logging.getLogger(__name__)


def config_app(app, credentials):

    app.debug = credentials["DEBUG"]

    # Load app secret and convert to byte string
    app.secret_key = credentials["app_secret"].encode()
    app.config['WTF_CSRF_ENABLED'] = False

    # API related configuration
    os.environ["PORT"] = str(credentials["api"]["port"])
    os.environ["API_HOST"] = credentials["api"]["host"]
    os.environ["API_EP_CTRL_VOC"] = credentials["api"]["endpoint"]["ctrl_vocs"]
    os.environ["API_EP_PROPERTY"] = credentials["api"]["endpoint"]["properties"]
    os.environ["API_EP_FORM"] = credentials["api"]["endpoint"]["forms"]
    os.environ["API_EP_STUDY"] = credentials["api"]["endpoint"]["studies"]
    os.environ["API_EP_USER"] = credentials["api"]["endpoint"]["users"]

    # Disable checking access token
    app.config["CHECK_ACCESS_TOKEN"] = credentials.get("check_access_token", True)

    # Load mongo database credentials
    app.config["MONGODB_DB"] = credentials["database"]["mongodb"]["database"]
    app.config["MONGODB_HOST"] = credentials["database"]["mongodb"]["hostname"]
    app.config["MONGODB_PORT"] = credentials["database"]["mongodb"]["port"]
    app.config["MONGODB_USERNAME"] = credentials["database"]["mongodb"]["username"]
    app.config["MONGODB_PASSWORD"] = credentials["database"]["mongodb"]["password"]
    app.config["MONGODB_CONNECT"] = False

    # Load mongo collection names
    app.config["MONGODB_COL_PROPERTY"] = credentials["database"]["mongodb"]["collection"]["property"]
    app.config["MONGODB_COL_CTRL_VOC"] = credentials["database"]["mongodb"]["collection"]["ctrl_voc"]
    app.config["MONGODB_COL_FORM"] = credentials["database"]["mongodb"]["collection"]["form"]
    app.config["MONGODB_COL_USER"] = credentials["database"]["mongodb"]["collection"]["user"]
    app.config["MONGODB_COL_STUDY"] = credentials["database"]["mongodb"]["collection"]["study"]


def clear_environmental_variables():

    for key in ["PORT", "API_HOST"]:
        if key in os.environ:
            del os.environ[key]


def create_app(config="DEVELOPMENT"):

    atexit.register(clear_environmental_variables)

    app = Flask(__name__)

    credentials = load_credentials()
    config_app(app, credentials[config])

    # Restplus API
    app.config["ERROR_404_HELP"] = False

    con = connect(app.config["MONGODB_DB"],
                  host=app.config["MONGODB_HOST"],
                  port=app.config["MONGODB_PORT"],
                  username=app.config["MONGODB_USERNAME"],
                  password=app.config["MONGODB_PASSWORD"],
                  )

    # TODO: Find a better way to set the collection names
    from metadata_registration_api.model import Property, ControlledVocabulary, Form, User, Study
    # noinspection PyProtectedMember
    Property._meta["collection"] = app.config["MONGODB_COL_PROPERTY"]
    # noinspection PyProtectedMember
    ControlledVocabulary._meta["collection"] = app.config["MONGODB_COL_CTRL_VOC"]
    # noinspection PyProtectedMember
    Form._meta["collection"] = app.config["MONGODB_COL_FORM"]
    # noinspection PyProtectedMember
    User._meta["collection"] = app.config["MONGODB_COL_USER"]
    # noinspection PyProtectedMember
    Study._meta["collection"] = app.config["MONGODB_COL_STUDY"]

    api.init_app(app,
                 title="Metadata Registration API",
                 contact="Rafael Müller",
                 contact_email="rafael.mueller@roche.com",
                 description="An API to register and manage study related metadata."
                             "\n\n"
                             "The code is available here: https://github.roche.com/BEDA/metadata_registration_api. "
                             "Any issue reports or feature requests are appreciated.",
                 )

    # Initialize FormManager
    url = "http://" + os.environ["API_HOST"] + ":" + str(os.environ["PORT"])
    app.config["URL"] = url
    data_store = ApiDataStore()
    app.form_manager = FormManager(data_store=data_store, initial_load=False)

    app.study_state_machine = context.Context()

    logger.info(f"Created Flask API and exposed {url}")

    return app


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description="Start property microservice")
    parser.add_argument("--config", type=str,
                        default="DEVELOPMENT",
                        help="Mode in which the application should start",
                        )

    args = parser.parse_args()

    app = create_app(**vars(args))
    app.run(host="0.0.0.0", port=os.environ["PORT"])

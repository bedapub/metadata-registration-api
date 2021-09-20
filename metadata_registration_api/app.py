from gevent import monkey

monkey.patch_all()
import os
import logging

from flask import Flask
from flask_cors import CORS
from mongoengine import connect

from metadata_registration_lib.other_utils import str_to_bool
from metadata_registration_api.datastores import MongoEngineDataStore
from metadata_registration_api.mongo_utils import get_states
from metadata_registration_api.api import api

from dynamic_form import FormManager
from study_state_machine import context

logger = logging.getLogger(__name__)


def config_app(app):

    required_env_variables = [
        "APP_SECRET",
        "PORT",
        "API_HOST",
        "API_EP_CTRL_VOC",
        "API_EP_PROPERTY",
        "API_EP_FORM",
        "API_EP_STUDY",
        "API_EP_USER",
        "MONGODB_DB",
        "MONGODB_HOST",
        "MONGODB_PORT",
        "MONGODB_USERNAME",
        "MONGODB_PASSWORD",
        "MONGODB_COL_PROPERTY",
        "MONGODB_COL_CTRL_VOC",
        "MONGODB_COL_FORM",
        "MONGODB_COL_USER",
        "MONGODB_COL_STUDY",
        "MONGODB_COL_STATE",
    ]

    for env_variable in required_env_variables:
        if not env_variable in os.environ:
            raise Exception(f"The environment variable {env_variable} is required")

    # Load app secret and convert to byte string
    app.secret_key = os.environ["APP_SECRET"].encode()
    app.config["WTF_CSRF_ENABLED"] = False

    # Disable checking access token
    app.config["CHECK_ACCESS_TOKEN"] = str_to_bool(
        os.getenv("CHECK_ACCESS_TOKEN", "true")
    )

    # Load mongo database credentials
    app.config["MONGODB_DB"] = os.environ["MONGODB_DB"]
    app.config["MONGODB_HOST"] = os.environ["MONGODB_HOST"]
    app.config["MONGODB_PORT"] = int(os.environ["MONGODB_PORT"])
    app.config["MONGODB_USERNAME"] = os.environ["MONGODB_USERNAME"]
    app.config["MONGODB_PASSWORD"] = os.environ["MONGODB_PASSWORD"]
    app.config["MONGODB_CONNECT"] = False

    # Load mongo collection names
    app.config["MONGODB_COL_PROPERTY"] = os.environ["MONGODB_COL_PROPERTY"]
    app.config["MONGODB_COL_CTRL_VOC"] = os.environ["MONGODB_COL_CTRL_VOC"]
    app.config["MONGODB_COL_FORM"] = os.environ["MONGODB_COL_FORM"]
    app.config["MONGODB_COL_USER"] = os.environ["MONGODB_COL_USER"]
    app.config["MONGODB_COL_STUDY"] = os.environ["MONGODB_COL_STUDY"]
    app.config["MONGODB_COL_STATE"] = os.environ["MONGODB_COL_STATE"]

    # Elastic search
    app.config["ES"] = {
        "HOST": os.environ.get("ES_HOST"),
        "PORT": os.environ.get("ES_PORT"),
        "INDEX": os.environ.get("ES_INDEX"),
        "SECURE": str_to_bool(os.environ.get("ES_SECURE", "false")),
        "USERNAME": os.environ.get("ES_USERNAME"),
        "PASSWORD": os.environ.get("ES_PASSWORD"),
        "USE": os.environ.get("ES_USE"),
    }


def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})

    config_app(app)

    # Restplus API
    app.config["ERROR_404_HELP"] = False

    app.mongo_client = connect(
        app.config["MONGODB_DB"],
        host=app.config["MONGODB_HOST"],
        port=app.config["MONGODB_PORT"],
        username=app.config["MONGODB_USERNAME"],
        password=app.config["MONGODB_PASSWORD"],
    )

    # There might be a better way to set the collection names
    # Either do this or read ENV  variables in models definition in "meta" dict
    # Another option would be to use factories: https://github.com/MongoEngine/mongoengine/issues/2065
    from metadata_registration_api.model import (
        Property,
        ControlledVocabulary,
        Form,
        User,
        Study,
    )

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

    api.init_app(
        app,
        title="Metadata Registration API",
        contact="Rafael Müller",
        contact_email="rafa.molitoris@gmail.com",
        description="An API to register and manage study related metadata."
        "\n\n"
        "The code is available here: https://github.com/BEDApub/metadata-registration-api. "
        "Any issue reports or feature requests are appreciated.",
    )

    # Initialize FormManager
    url = "https://" + os.environ["API_HOST"] + ":" + str(os.environ["PORT"])
    app.config["URL"] = url
    # data_store = ApiDataStore()
    data_store = MongoEngineDataStore(form_model=Form)
    app.form_manager = FormManager(data_store=data_store, initial_load=False)

    available_states = get_states(app=app, q={})
    app.study_state_machine = context.Context(available_states=available_states)

    logger.info(f"Created Flask API and exposed {url}")

    return app


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description="Start property microservice")

    args = parser.parse_args()

    app = create_app(**vars(args))
    app.run(host="0.0.0.0", port=os.environ["PORT"])

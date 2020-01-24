import os

from flask import Flask
from mongoengine import connect

from metadata_registration_api.my_utils import load_credentials
from dynamic_form import FormManager, ApiDataStore


def config_app(app, credentials):

    app.debug = credentials["DEBUG"]

    # Load app secret and convert to byte string
    app.secret_key = credentials["app_secret"].encode()

    app.config["PORT"] = credentials["api"]["port"]
    app.config["API_HOST"] = credentials["api"]["host"]

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


def create_app(config="DEVELOPMENT"):
    app = Flask(__name__)

    credentials = load_credentials()
    config_app(app, credentials[config])

    # Restplus API
    app.config["ERROR_404_HELP"] = False

    connect(app.config["MONGODB_DB"],
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

    from metadata_registration_api.api import api
    api.init_app(app,
                 title="API for properties, controlled vocabulary, forms and studies.",
                 contact="Rafael Müller",
                 contact_email="rafael.mueller@roche.com",
                 description="An API to manage properties and controlled vocabularies."
                             "\n\n"
                             "The code is available here: https://github.roche.com/rafaelsm/ApiService. Any issue "
                             "reports or feature requests are appreciated.",
                 )

    # Initialize FormManager
    url = "http://127.0.0.1:5001"
    ds = ApiDataStore(url=url)
    app.form_manager = FormManager(ds_adapter=ds, initial_load=False)

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
    app.run(host="0.0.0.0", port=app.config["PORT"])

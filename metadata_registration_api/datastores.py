import logging
import os
from urllib.parse import urljoin
from distutils.util import strtobool

import requests
from flask_restx import marshal


from dynamic_form import IDataStore
from dynamic_form.errors import DataStoreException

logger = logging.getLogger(__name__)


class ApiDataStore(IDataStore):
    """Concrete implementation for a data store that uses an API"""

    def __init__(self, url=None):

        if not url:
            http_prefix = (
                "https" if strtobool(os.environ.get("SSL", "false")) else "http"
            )
            self.url = f"{http_prefix}://{os.environ['API_HOST']}:{os.environ['PORT']}"
        else:
            self.url = url
        self.form_endpoint = urljoin(self.url, os.environ["API_EP_FORM"])

    def load_form(self, identifier):
        result = requests.get(f"{self.form_endpoint}/id/{identifier}")
        return self._process_results(result, f"Fail to load form (id:{identifier})")

    def load_form_by_name(self, name):
        header = {"X-Fields": "name, id"}
        result = requests.get(self.form_endpoint, headers=header)

        if result.status_code != 200:
            error_msg = f"Fail to load all forms [{result.status_code}] {result.json()}"
            logger.error(error_msg)
            raise DataStoreException(error_msg)

        try:
            form_entry = next(
                filter(lambda entry: entry["name"] == name, result.json())
            )
            res = requests.get(f"{self.form_endpoint}/id/{form_entry['id']}")
            return self._process_results(res, f"Fail to load form (name:{name})")

        except StopIteration as e:
            error_msg = f"Fail to find form in database (name:{name}, data store: {self.__class__.__name__})"
            logger.error(error_msg)
            raise DataStoreException(error_msg) from e

    def load_forms(self):
        """Load all forms from the API"""
        results = requests.get(self.form_endpoint)
        return self._process_results(results)

    def insert_form(self, form_template):
        raise NotImplementedError

    def find_form(self, *args, id=None, **kwargs):
        raise NotImplementedError

    def deprecate_form(self, identifier):
        result = requests.delete(f"{self.form_endpoint}/id/{identifier}")
        return self._process_results(
            result, f"Fail to deprecated form (id:{identifier}"
        )

    @staticmethod
    def _process_results(results, error_message="Fail to get results", status_code=200):

        if results.status_code != status_code:
            error_msg = f"{error_message} [{results.status_code}] {results.json()}"
            logger.error(error_msg)
            raise DataStoreException(error_message)

        return results.json()


class MongoEngineDataStore(IDataStore):
    """Concrete implementation for a data store that uses an mongoengine"""

    def __init__(self, form_model=None, marshal_model=None):
        self.form_model = form_model

        if marshal_model is None:
            from metadata_registration_api.api.api_form import form_model_id

            self.marshal_model = form_model_id

    def load_form(self, identifier):
        res = self.form_model.objects.get(id=identifier)
        return marshal(res, self.marshal_model)

    def load_form_by_name(self, name):
        try:
            res = self.form_model.objects.get(name=name)
            return marshal(res, self.marshal_model)

        except Exception as e:
            error_msg = f"Fail to find form in database (name:{name}, data store: {self.__class__.__name__})"
            logger.error(error_msg)
            raise DataStoreException(error_msg) from e

    def load_forms(self):
        """Load all forms"""
        res = self.form_model.objects(deprecated=False)
        return marshal(list(res), self.marshal_model)

    def insert_form(self, form_template):
        raise NotImplementedError

    def find_form(self, *args, id=None, **kwargs):
        raise NotImplementedError

    def deprecate_form(self, identifier):
        raise NotImplementedError

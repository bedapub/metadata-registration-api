import os
from urllib.parse import urljoin

from metadata_registration_lib import es_utils


def index_study(config, study_data, action):
    """
    Index the study data in form format on Elastic Search using the LIB functions
    Parameters:
        - config (dict): app.config configuration dict
        - study_data (dict): Study data in form format
        - action (str): "add" or "update"
    """
    try:
        es_utils.index_study(
            es_index_url=es_utils.get_es_index_url(config["ES"]),
            es_auth=es_utils.get_es_auth(config["ES"]),
            study_data=study_data,
            action=action,
            cv_url=urljoin(config["URL"], os.environ["API_EP_CTRL_VOC"])
        )
    except:
        pass


def remove_study_from_index(config, study_id):
    """
    Delete a study fom the Elastic Search index from its id using the LIB functions
    Parameters:
        - config (dict): app.config configuration dict
        - study_id (str): id of the study to delete
    """
    try:
        es_utils.remove_study_from_index(
            es_index_url=es_utils.get_es_index_url(config["ES"]),
            es_auth=es_utils.get_es_auth(config["ES"]),
            study_id=study_id,
        )
    except:
        pass

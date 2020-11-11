import os
from urllib.parse import urljoin

from flask import current_app as app
from flask import after_this_request, Response, send_file
from flask_restx import Namespace, reqparse, Resource, inputs

from metadata_registration_lib.api_utils import map_key_value
from metadata_registration_lib.data_utils import NormConverter
from metadata_registration_lib.file_utils import write_file_from_denorm_data_2

from metadata_registration_api.api.api_utils import (get_json, get_property_map,
    get_cv_items_name_to_label_map)
from .api_study import api

import tempfile
import json
from collections import OrderedDict

api = Namespace("Studies export", description="Study related file exports")

# Common parsers
# ----------------------------------------------------------------------------------------------------------------------
export_get_parser = reqparse.RequestParser()
export_get_parser.add_argument(
    "header_sep",
    type=str,
    location="args",
    default="__",
    help="Header sep",
)
export_get_parser.add_argument(
    "format",
    type=str,
    location="args",
    default="xlsx",
    choices=("xlsx", "tsv", "csv"),
    help="Header sep",
)
export_get_parser.add_argument(
    "prop_to_ignore",
    type=str,
    location="args",
    default="uuid",
    help="Comma separated list of property names to ignore",
)
export_get_parser.add_argument(
    "use_cv_labels",
    type=inputs.boolean,
    location="args",
    default=True,
    help="If true, will repalce CV item names by their labels",
)
export_get_parser.add_argument(
    "prettify_headers",
    type=inputs.boolean,
    location="args",
    default=True,
    help="If true, will replace property name by labels and header suffixes by nice preffixes",
)

# Routes
# ----------------------------------------------------------------------------------------------------------------------
@api.route("/id/<study_id>/samples/download")
@api.param("study_id", "The study identifier")
class DownloadSamples(Resource):
    _get_parser = export_get_parser

    @api.doc(parser=_get_parser)
    def get(self, study_id):
        """Download samples in a denormalized file"""
        args = self._get_parser.parse_args()
        header_sep = args["header_sep"].strip()

        study_endpoint = urljoin(app.config["URL"], os.environ["API_EP_STUDY"])

        header_prefix_to_suffix = {
            "sample": "SAM",
            "sample__individual__treatment": "TRE > IND",
            "sample__treatment": "TRE > SAM",
            "sample__individual": "IND",
        }

        # 1. Get samples data
        url = f"{study_endpoint}/id/{study_id}?entry_format=form"
        study_json = get_json(url)

        try:
            samples = study_json["entries"]["samples"]
        except:
            raise Exception(f"The given study '{study_id}' doesn't have samples data")

        # 2. Convert to flat format (denormalized)
        converter = NormConverter(nested_data=samples)
        samples_flat = converter.get_denorm_data_2_from_nested(
            vars_to_denorm=[],
            use_parent_key=True,
            sep=header_sep,
            initial_parent_key="sample",
            missing_value="",
        )

        return download_denorm_file(
            request_args=args,
            data=samples_flat,
            header_prefix_to_suffix=header_prefix_to_suffix,
            file_name="samples",
        )



@api.route("/id/<study_id>/datasets/id/<dataset_uuid>/exp/download")
@api.route("/datasets/<dataset_uuid>/exp/download",
    doc={"description": "Alias route for a getting samples without study_id"})
@api.param("study_id", "The study identifier")
@api.param("dataset_uuid", "The dataset identifier")
class DownloadExperiments(Resource):
    _get_parser = export_get_parser

    @api.doc(parser=_get_parser)
    def get(self, dataset_uuid, study_id=None):
        """Download experiments in a denormalized file"""
        args = self._get_parser.parse_args()
        header_sep = args["header_sep"].strip()

        study_endpoint = urljoin(app.config["URL"], os.environ["API_EP_STUDY"])

        header_prefix_to_suffix = {
            "": "EXP",
            "samples": "SAM",
            "samples__individual__treatment": "TRE > IND",
            "samples__treatment": "TRE > SAM",
            "samples__individual": "IND",
        }

        # 1. Get the experiments data
        if study_id is not None:
            dataset_url = f"{study_endpoint}/id/{study_id}/datasets/id/{dataset_uuid}?entry_format=form"
        else:
            dataset_url = f"{study_endpoint}/datasets/id/{dataset_uuid}?entry_format=form"
        experiments = get_json(dataset_url)["experiments"]

        # 2. Convert to flat format (denormalized)
        converter = NormConverter(nested_data=experiments)
        experiments_flat = converter.get_denorm_data_2_from_nested(
            vars_to_denorm=["samples"],
            use_parent_key=True,
            sep=header_sep,
            initial_parent_key="",
            missing_value="",
        )

        return download_denorm_file(
            request_args=args,
            data=experiments_flat,
            header_prefix_to_suffix=header_prefix_to_suffix,
            file_name="experiments",
        )


def download_denorm_file(request_args, data, header_prefix_to_suffix, file_name):
    """
    Download samples in a denormalized file
    Arguments
        - request = flask request
        - data in denormalized 2 format (see NormConverter.get_denorm_data_2_from_nested)
        - header_prefix_to_suffix = dict to replace headers with nice suffixes
        - file_name = exported file name (without extension)
    Query arguments
        - header_sep = seaparator used to join header across nesting: samples__treatment__treatment_id
            Default: __
        - format = file formats supported for the file export (xlsx, tsv or csv)
            Default: xlsx
        - prop_to_ignore = comma separated list of property names to ignore (default to "uuid")
            Default: uuid
        - use_cv_labels = true / false
            ==> If true, will repalce CV item names by their labels
            Default: true
        - prettify_headers = true / false
            ==> If true, will replace property name by labels and header suffixes by nice preffixes
            Default: true
    """
    try:
        # 1. Parse query parameters
        header_sep = request_args["header_sep"].strip()
        file_format = request_args["format"].strip().lower()
        use_cv_labels = request_args["use_cv_labels"]
        prettify_headers = request_args["prettify_headers"]
        prop_to_ignore = [
            p.strip().lower()
            for p in request_args["prop_to_ignore"].split(",")
            if p.strip().lower() != ""
        ]

        # 2. Convert CV item names to labels
        if use_cv_labels:
            prop_name_to_data_type = get_property_map(key="name", value="value_type")
            cv_items_name_to_label_map = get_cv_items_name_to_label_map()

            for header, data_list in data.items():
                property_name = header.split(header_sep)[-1]
                prop_value_type = prop_name_to_data_type[property_name]

                if prop_value_type["data_type"] == "ctrl_voc":
                    cv_name = prop_value_type["controlled_vocabulary"]["name"]
                    cv_items_map = cv_items_name_to_label_map[cv_name]
                    data[header] = [cv_items_map.get(v, v) for v in data_list]

        # 5. Ignore certain properties
        for header in list(data.keys()):
            property_name = header.split(header_sep)[-1]
            if property_name in prop_to_ignore:
                data.pop(header)

        # 6. Update headers
        if prettify_headers:
            prop_name_to_label = get_property_map(key="name", value="label")
            old_data = data
            data = OrderedDict()
            for header, data_list in old_data.items():
                split_header = header.rsplit(header_sep, 1)
                prefix = split_header[0] if len(split_header) > 1 else ""
                prop_name = (
                    split_header[1] if len(split_header) > 1 else split_header[0]
                )
                prop_label = prop_name_to_label[prop_name]
                suffix = header_prefix_to_suffix[prefix]
                new_header = f"{prop_label} ({suffix})"
                data[new_header] = data_list

        # 7. Write file
        f = tempfile.NamedTemporaryFile(mode="w", delete=False)
        write_file_from_denorm_data_2(f, data, file_format)
        f.close()

        @after_this_request
        def cleanup(response):
            os.unlink(f.name)
            print(f.name)
            return response

        response = send_file(
            f.name, as_attachment=True, attachment_filename=f"{file_name}.{file_format}"
        )
        response.headers.extend({"Cache-Control": "no-cache"})
        return response

    except Exception as e:
        return Response(
            json.dumps({"error": str(e)}), status=500, mimetype="application/json"
        )

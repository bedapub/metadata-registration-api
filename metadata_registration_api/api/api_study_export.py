import os
from urllib.parse import urljoin

from flask import current_app as app
from flask import after_this_request, Response, request, send_file
from flask_restx import Namespace, reqparse, Resource, inputs

from metadata_registration_lib.api_utils import map_key_value_from_dict_list
from metadata_registration_lib.data_utils import NormConverter, expand_json_strings
from metadata_registration_lib.file_writing_utils import write_file_from_denorm_data_2

from metadata_registration_api.api.api_utils import (
    get_json,
    get_property_map,
    get_cv_items_map,
)
from .api_study_dataset import find_study_id_from_lvl1_uuid
from .decorators import token_required

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
    help="File format",
)
export_get_parser.add_argument(
    "include_study_data",
    type=inputs.boolean,
    location="args",
    default=True,
    help="If true, will append study level data to each row",
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
    help="If true, will replace CV item names by their labels",
)
export_get_parser.add_argument(
    "prettify_headers",
    type=inputs.boolean,
    location="args",
    default=True,
    help="If true, will replace property name by labels and header prefixes by shorter suffixes",
)

export_get_parser_rdt = export_get_parser
export_get_parser_rdt.add_argument(
    "include_dataset_data",
    type=inputs.boolean,
    location="args",
    default=True,
    help="If true, will append dataset level data to each row",
)

# Routes
# ----------------------------------------------------------------------------------------------------------------------
@api.route("/id/<study_id>/samples/download")
@api.param("study_id", "The study identifier")
class DownloadSamples(Resource):
    _get_parser = export_get_parser

    @token_required
    @api.doc(parser=_get_parser)
    def get(self, study_id, user=None):
        """Download samples in a denormalized file"""
        args = self._get_parser.parse_args()
        prettify_headers = args["prettify_headers"]
        header_sep = "__" if prettify_headers else args["header_sep"].strip()

        study_endpoint = urljoin(app.config["URL"], os.environ["API_EP_STUDY"])

        header_prefix_to_suffix = {
            "": "STU",
            "samples": "SAM",
            "samples__individual__treatment": "TRE > IND",
            "samples__treatment": "TRE > SAM",
            "samples__individual": "IND",
        }

        # 1. Get study and samples data
        study_url = f"{study_endpoint}/id/{study_id}?entry_format=form"

        try:
            study = get_json(study_url, headers=request.headers)["entries"]
        except:
            raise Exception(f"Error retrieving study data from id '{study_id}'")

        if not "samples" in study:
            raise Exception(f"The given study '{study_id}' doesn't have samples data")

        # 2. Removing data we don't want in the file
        # Removing datasets data to avoid too much denormalization and duplication of lines
        if "datasets" in study:
            study["datasets"] = len(study["datasets"])

        # 3. Expand JSON string properties
        study = expand_json_strings(study)

        # 4. Convert to flat format (denormalized)
        if args["include_study_data"]:
            converter = NormConverter(nested_data=study)
            data_flat = converter.get_denorm_data_2_from_nested(
                vars_to_denorm=["samples"],
                use_parent_key=True,
                sep=header_sep,
                initial_parent_key="",
                missing_value="",
            )
        else:
            converter = NormConverter(nested_data=study["samples"])
            data_flat = converter.get_denorm_data_2_from_nested(
                vars_to_denorm=[],
                use_parent_key=True,
                sep=header_sep,
                initial_parent_key="samples",
                missing_value="",
            )

        return download_denorm_file(
            request_args=args,
            data=data_flat,
            header_prefix_to_suffix=header_prefix_to_suffix,
            file_name="samples",
        )


@api.route("/id/<study_id>/datasets/id/<dataset_uuid>/rdt/download")
@api.route(
    "/datasets/<dataset_uuid>/rdt/download",
    doc={"description": "Alias route for a getting samples without study_id"},
)
@api.param("study_id", "The study identifier")
@api.param("dataset_uuid", "The dataset identifier")
class DownloadReadouts(Resource):
    _get_parser = export_get_parser_rdt

    @token_required
    @api.doc(parser=_get_parser)
    def get(self, dataset_uuid, study_id=None, user=None):
        """Download readouts in a denormalized file"""
        args = self._get_parser.parse_args()
        prettify_headers = args["prettify_headers"]
        header_sep = "__" if prettify_headers else args["header_sep"].strip()

        study_endpoint = urljoin(app.config["URL"], os.environ["API_EP_STUDY"])

        header_prefix_to_suffix = {
            "": "STU",
            "datasets": "DAT",
            "datasets__readouts": "RDT",
            "datasets__readouts__samples": "SAM",
            "datasets__readouts__samples__individual__treatment": "TRE > IND",
            "datasets__readouts__samples__treatment": "TRE > SAM",
            "datasets__readouts__samples__individual": "IND",
        }

        # 1. Get the study, dataset and readouts data
        if study_id is None:
            prop_name_to_id = get_property_map(key="name", value="id")
            study_id = find_study_id_from_lvl1_uuid(
                "dataset", dataset_uuid, prop_name_to_id
            )

        study_url = f"{study_endpoint}/id/{study_id}?entry_format=form"
        study = get_json(study_url, headers=request.headers)["entries"]

        for d in study["datasets"]:
            if d["uuid"] == dataset_uuid:
                dataset = d
                break
        else:
            raise Exception(f"Dataset '{dataset_uuid}' not found in study '{study_id}'")

        if not "readouts" in dataset:
            raise Exception(f"Dataset '{dataset_uuid}' doesn't have readouts data")

        if not "samples" in study:
            raise Exception(f"The given study '{study_id}' doesn't have samples data")

        # 2. Replace sample UUIDs in readouts by nested sample objects
        sam_uuid_to_obj = map_key_value_from_dict_list(
            study["samples"], key="uuid", value=None
        )
        try:
            for readout in dataset["readouts"]:
                readout["samples"] = [
                    sam_uuid_to_obj[uuid] for uuid in readout["samples"]
                ]
        except:
            message = "Readouts sample UUIDs did not match the samples of the study,"
            message += " please update the readouts if the samples have been changed"
            raise Exception(message)

        # 3. Removing data we don't want in the file
        # 3.1. Relevant samples are in dataset > readouts
        del study["samples"]

        # 3.2. Removing processing event data to avoid too much denormalization and duplication of lines
        if "process_events" in dataset:
            dataset["process_events"] = len(dataset["process_events"])

        # 3.3. Only interested in one dataset
        study["datasets"] = dataset

        # 4. Expand JSON string properties
        study = expand_json_strings(study)
        dataset = expand_json_strings(dataset)

        # 5. Convert to flat format (denormalized)
        # 5.1. Readouts
        converter = NormConverter(nested_data=study["datasets"]["readouts"])
        data_flat = converter.get_denorm_data_2_from_nested(
            vars_to_denorm=["samples"],
            use_parent_key=True,
            sep=header_sep,
            initial_parent_key="datasets__readouts",
            missing_value="",
        )

        nb_lines = len(list(data_flat.values())[0])
        # 5.2. Add dataset data
        if args["include_dataset_data"]:
            for dataset_prop, value in dataset.items():
                if not dataset_prop in ["readouts"]:
                    data_flat[f"datasets__{dataset_prop}"] = [value] * nb_lines

        # 5.3. Add study data
        if args["include_study_data"]:
            for study_prop, value in study.items():
                if not study_prop in ["datasets"]:
                    data_flat[study_prop] = [value] * nb_lines

        return download_denorm_file(
            request_args=args,
            data=data_flat,
            header_prefix_to_suffix=header_prefix_to_suffix,
            file_name="readouts",
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
            ==> If true, will replace CV item names by their labels
            Default: true
        - prettify_headers = true / false
            ==> If true, will replace property name by labels and header prefixes by shorter suffixes
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

        # 2. Ignore certain properties
        for header in list(data.keys()):
            property_name = header.split(header_sep)[-1]
            if property_name in prop_to_ignore:
                data.pop(header)

        # 3. Convert CV item names to labels
        if use_cv_labels:
            prop_name_to_data_type = get_property_map(
                key="name",
                value="value_type",
                mask="name, value_type{data_type, controlled_vocabulary{name}}",
            )
            cv_items_name_to_label_map = get_cv_items_map(key="name", value="label")

            for header, data_list in data.items():
                property_name = header.split(header_sep)[-1]
                prop_value_type = prop_name_to_data_type.get(property_name, None)

                if (
                    prop_value_type is not None
                    and prop_value_type["data_type"] == "ctrl_voc"
                ):
                    cv_name = prop_value_type["controlled_vocabulary"]["name"]
                    cv_items_map = cv_items_name_to_label_map[cv_name]
                    new_data_list = []
                    for value in data_list:
                        if type(value) == list:
                            new_data_list.append(
                                [cv_items_map.get(v, v) for v in value]
                            )
                        else:
                            new_data_list.append(cv_items_map.get(value, value))
                    data[header] = new_data_list

        # 4. Stringify simple lists
        for header, data_list in data.items():
            if type(data_list[0]) == list:
                data[header] = [", ".join(map(str, v)) for v in data_list]

        # 5. Update headers
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
                if prop_name in prop_name_to_label:
                    prop_label = prop_name_to_label[prop_name]
                else:
                    prop_label = prop_name

                if prefix in header_prefix_to_suffix:
                    suffix = header_prefix_to_suffix[prefix]
                    new_header = f"{prop_label} ({suffix})"
                else:
                    new_header = f"{prop_label}"

                data[new_header] = data_list

        # 6. Write file
        f = tempfile.NamedTemporaryFile(mode="w", delete=False)
        write_file_from_denorm_data_2(f, data, file_format)
        f.close()

        @after_this_request
        def cleanup(response):
            os.unlink(f.name)
            return response

        response = send_file(
            f.name, as_attachment=True, attachment_filename=f"{file_name}.{file_format}"
        )
        response.headers.extend({"Cache-Control": "no-cache"})
        return response

    except Exception as e:
        from traceback import print_exc

        print_exc()
        return Response(
            json.dumps({"error": str(e)}), status=500, mimetype="application/json"
        )

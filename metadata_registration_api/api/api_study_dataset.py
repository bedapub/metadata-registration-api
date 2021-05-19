import uuid

from flask_restx import Namespace, Resource, marshal
from flask_restx import reqparse

from metadata_registration_lib.api_utils import (reverse_map, FormatConverter,
    Entry, NestedEntry, NestedListEntry)

from metadata_registration_api.api.api_utils import get_property_map
from .api_study import (entry_format_param, entry_model_prop_id, entry_model_form_format,
    study_model, nested_study_entry_model_prop_id)
from .api_study import validate_form_format_against_form, update_study
from .decorators import token_required
from ..model import Study

api = Namespace("Datasets", description="Dataset related operations")


# Routes
# ----------------------------------------------------------------------------------------------------------------------

@api.route("/id/<study_id>/datasets")
@api.param("study_id", "The study identifier")
class ApiStudyDataset(Resource):
    _get_parser = reqparse.RequestParser()
    _get_parser.add_argument("entry_format", **entry_format_param)

    @token_required
    @api.response("200 - api", "Success (API format)", [[entry_model_prop_id]])
    @api.response("200 - form", "Success (form format)", [entry_model_form_format])
    @api.doc(parser=_get_parser)
    def get(self, study_id, user=None):
        """ Fetch a list of all datasets for a given study """
        args = self._get_parser.parse_args()

        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        prop_map = get_property_map(key="id", value="name")

        # The converter is used for its get_entry_by_name() method
        study_converter = FormatConverter(mapper=prop_map)
        study_converter.add_api_format(study_json["entries"])

        datasets_entry = study_converter.get_entry_by_name("datasets")

        if datasets_entry is not None:
            # The "datasets" entry is a NestedListEntry (return list of list)
            if args["entry_format"] == "api":
                return datasets_entry.get_api_format()
            elif args["entry_format"] == "form":
                return datasets_entry.get_form_format()
        else:
            return []

    @token_required
    @api.expect(nested_study_entry_model_prop_id)
    def post(self, study_id, user=None):
        """ Add a new dataset for a given study """
        payload = api.payload

        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # 1. Split payload
        form_name = payload["form_name"]
        entries = payload["entries"]
        entry_format = payload.get("entry_format", "api")

        # 2. Get study data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # 3. Format and clean dataset data
        if entry_format == "api":
            dataset_converter = FormatConverter(mapper=prop_id_to_name)
            dataset_converter.add_api_format(entries)
        elif entry_format == "form":
            dataset_converter = FormatConverter(mapper=prop_name_to_id)
            dataset_converter.add_form_format(entries)

        dataset_converter.clean_data()

        # 4. Generate UUID
        dataset_uuid = str(uuid.uuid1())
        dataset_converter.entries.insert(0,
            Entry(FormatConverter(prop_name_to_id))\
                .add_form_format("uuid", dataset_uuid)
        )

        dataset_nested_entry = NestedEntry(dataset_converter)
        dataset_nested_entry.value = dataset_converter.entries

        # 5. Check if "datasets" entry already exist study, creates it if it doesn't
        datasets_entry = study_converter.get_entry_by_name("datasets")

        if datasets_entry is not None:
            datasets_entry.value.value.append(dataset_nested_entry)
        else:
            datasets_entry = Entry(FormatConverter(prop_name_to_id))\
                .add_form_format("datasets", [dataset_nested_entry.get_form_format()])
            study_converter.entries.append(datasets_entry)

        # 6. Validate dataset data against form
        validate_form_format_against_form(form_name, dataset_converter.get_form_format())

        # 7. Update study state, data and ulpoad on DB
        message = "Added dataset"
        update_study(study, study_converter, payload, message, user)
        return {"message": message, "uuid": dataset_uuid}, 201


@api.route("/id/<study_id>/datasets/id/<dataset_uuid>", strict_slashes=False)
@api.route("/datasets/id/<dataset_uuid>", strict_slashes=False,
    doc={"description": "Alias route for a specific dataset without study_id"})
@api.param("study_id", "The study identifier")
@api.param("dataset_uuid", "The dataset identifier")
class ApiStudyDatasetId(Resource):
    _get_parser = reqparse.RequestParser()
    _get_parser.add_argument("entry_format", **entry_format_param)

    @token_required
    @api.response("200 - api", "Success (API format)", [entry_model_prop_id])
    @api.response("200 - form", "Success (form format)", entry_model_form_format)
    @api.doc(parser=_get_parser)
    def get(self, dataset_uuid, study_id=None, user=None):
        """ Fetch a specific dataset for a given study """
        args = self._get_parser.parse_args()

        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only dataset_uuid
        if study_id is None:
            study_id = find_study_id_from_dataset(dataset_uuid, prop_name_to_id)
            if study_id is None:
                raise Exception(f"Dataset not found in any study (uuid = {dataset_uuid})")

        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        # The converter is used for its get_entry_by_name() method
        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry = datasets_entry.value.find_nested_entry("uuid", dataset_uuid)[0]

        # The "dataset_nested_entry" entry is a NestedEntry (return list of dict)
        if args["entry_format"] == "api":
            return dataset_nested_entry.get_api_format()
        elif args["entry_format"] == "form":
            return dataset_nested_entry.get_form_format()

    @token_required
    @api.expect(nested_study_entry_model_prop_id)
    def put(self, dataset_uuid, study_id=None, user=None):
        """ Update a dataset for a given study """
        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only dataset_uuid
        if study_id is None:
            study_id = find_study_id_from_dataset(dataset_uuid, prop_name_to_id)
            if study_id is None:
                raise Exception(f"Dataset not found in any study (uuid = {dataset_uuid})")

        payload = api.payload

        # 1. Split payload
        form_name = payload["form_name"]
        entries = payload["entries"]
        entry_format = payload.get("entry_format", "api")

        # 2. Get study data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # 3. Get current dataset data
        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry = datasets_entry.value.find_nested_entry("uuid", dataset_uuid)[0]
        dataset_converter = FormatConverter(mapper=prop_id_to_name)
        dataset_converter.entries = dataset_nested_entry.value

        # 4. Get new dataset data
        if entry_format == "api":
            new_dataset_converter = FormatConverter(mapper=prop_id_to_name)
            new_dataset_converter.add_api_format(entries)
        elif entry_format == "form":
            new_dataset_converter = FormatConverter(mapper=prop_name_to_id)
            new_dataset_converter.add_form_format(entries)

        # 5. Clean new data and get entries to remove
        entries_to_remove = new_dataset_converter.clean_data()

        # 6. Update current dataset by adding, updating and deleting entries
        dataset_converter.add_or_update_entries(new_dataset_converter.entries)
        dataset_converter.remove_entries(entries=entries_to_remove)
        dataset_nested_entry.value = dataset_converter.entries

        # 7. Validate dataset data against form
        validate_form_format_against_form(form_name, dataset_converter.get_form_format())

        # 8. Update study state, data and ulpoad on DB
        message = "Updated dataset"
        update_study(study, study_converter, payload, message, user)
        return {"message": message}

    @token_required
    def delete(self, dataset_uuid, study_id=None, user=None):
        """ Delete a dataset from a study given its unique identifier """
        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only dataset_uuid
        if study_id is None:
            study_id = find_study_id_from_dataset(dataset_uuid, prop_name_to_id)
            if study_id is None:
                raise Exception(f"Dataset not found in any study (uuid = {dataset_uuid})")

        # 1. Get study data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # 2. Delete specific dataset
        datasets_entry = study_converter.get_entry_by_name("datasets")
        datasets_entry.value.delete_nested_entry("uuid", dataset_uuid)

        if len(datasets_entry.value.value) == 0:
            study_converter.remove_entries(prop_names=["datasets"])

        # 3. Update study state, data and ulpoad on DB
        message = f"Deleted dataset"
        update_study(study, study_converter, api.payload, message, user)

        return {"message": message}


@api.route("/id/<study_id>/datasets/id/<dataset_uuid>/pes")
@api.route("/datasets/id/<dataset_uuid>/pes",
    doc={"description": "Alias route for a dataset's PEs without study_id"})
@api.param("study_id", "The study identifier")
@api.param("dataset_uuid", "The dataset identifier")
class ApiStudyPE(Resource):
    _get_parser = reqparse.RequestParser()
    _get_parser.add_argument("entry_format", **entry_format_param)

    @token_required
    @api.response("200 - api", "Success (API format)", [[entry_model_prop_id]])
    @api.response("200 - form", "Success (form format)", [entry_model_form_format])
    @api.doc(parser=_get_parser)
    def get(self, dataset_uuid, study_id=None, user=None):
        """ Fetch a list of all processing events for a given study """
        args = self._get_parser.parse_args()

        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only dataset_uuid
        if study_id is None:
            study_id = find_study_id_from_dataset(dataset_uuid, prop_name_to_id)
            if study_id is None:
                raise Exception(f"Dataset not found in any study (uuid = {dataset_uuid})")

        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        # The converter is used for its get_entry_by_name() method
        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # Find dataset
        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry = datasets_entry.value.find_nested_entry("uuid", dataset_uuid)[0]

        # Find PEs
        pes_entry = dataset_nested_entry.get_entry_by_name("process_events")

        if pes_entry is not None:
            # The "process_events" entry is a NestedListEntry (return list of list)
            if args["entry_format"] == "api":
                return pes_entry.get_api_format()
            elif args["entry_format"] == "form":
                return pes_entry.get_form_format()
        else:
            return []

    @token_required
    @api.expect(nested_study_entry_model_prop_id)
    def post(self, dataset_uuid, study_id=None, user=None):
        """ Add a new processing event for a given dataset """
        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only dataset_uuid
        if study_id is None:
            study_id = find_study_id_from_dataset(dataset_uuid, prop_name_to_id)
            if study_id is None:
                raise Exception(f"Dataset not found in any study (uuid = {dataset_uuid})")

        payload = api.payload

        # 1. Split payload
        form_name = payload["form_name"]
        entries = payload["entries"]
        entry_format = payload.get("entry_format", "api")

        # 2. Get study and dataset data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)
        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])
        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry, dataset_position = datasets_entry.value.find_nested_entry("uuid", dataset_uuid)

        # 3. Format and clean processing event data
        if entry_format == "api":
            pe_converter = FormatConverter(mapper=prop_id_to_name)
            pe_converter.add_api_format(entries)
        elif entry_format == "form":
            pe_converter = FormatConverter(mapper=prop_name_to_id)
            pe_converter.add_form_format(entries)

        pe_converter.clean_data()

        # 4. Generate UUID
        pe_uuid = str(uuid.uuid1())
        pe_converter.entries.insert(0,
            Entry(FormatConverter(prop_name_to_id))\
                .add_form_format("uuid", pe_uuid)
        )

        pe_nested_entry = NestedEntry(pe_converter)
        pe_nested_entry.value = pe_converter.entries

        # 5. Check if "process_events"" entry already exist study, creates it if it doesn't
        pes_entry = dataset_nested_entry.get_entry_by_name("process_events")

        if pes_entry is not None:
            pes_entry.value.value.append(pe_nested_entry)
        else:
            pes_entry = Entry(FormatConverter(prop_name_to_id))\
                .add_form_format("process_events", [pe_nested_entry.get_form_format()])
            dataset_nested_entry.value.append(pes_entry)

        datasets_entry.value.value[dataset_position] = dataset_nested_entry

        # 6. Validate processing data against form
        validate_form_format_against_form(form_name, pe_converter.get_form_format())

        # 7. Update study state, data and ulpoad on DB
        message = "Added processing event"
        update_study(study, study_converter, payload, message, user)
        return {"message": message, "uuid": pe_uuid}, 201


@api.route("/id/<study_id>/datasets/id/<dataset_uuid>/pes/id/<pe_uuid>", strict_slashes=False)
@api.route("/pes/id/<pe_uuid>", strict_slashes=False,
    doc={"description": "Alias route for a specific PE without study_id or dataset_uuid"})
@api.param("study_id", "The study identifier")
@api.param("dataset_uuid", "The dataset identifier")
@api.param("pe_uuid", "The processing event identifier")
class ApiStudyPEId(Resource):
    _get_parser = reqparse.RequestParser()
    _get_parser.add_argument("entry_format", **entry_format_param)

    @token_required
    @api.response("200 - api", "Success (API format)", [entry_model_prop_id])
    @api.response("200 - form", "Success (form format)", entry_model_form_format)
    @api.doc(parser=_get_parser)
    def get(self, pe_uuid, study_id=None, dataset_uuid=None, user=None):
        """ Fetch a specific processing for a given dataset """
        args = self._get_parser.parse_args()

        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only pe_uuid
        if dataset_uuid is None:
            study_id, dataset_uuid = find_dataset_and_study_id_from_pe(
                pe_uuid = pe_uuid,
                prop_name_to_id = prop_name_to_id,
                prop_id_to_name = prop_id_to_name
            )
            if study_id is None or dataset_uuid is None:
                raise Exception(f"Processing event not found in any dataset (uuid = {pe_uuid})")

        # Used for helper route using only dataset_uuid
        if study_id is None:
            study_id = find_study_id_from_dataset(dataset_uuid, prop_name_to_id)
            if study_id is None:
                raise Exception(f"Dataset not found in any study (uuid = {dataset_uuid})")

        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        # The converter is used for its get_entry_by_name() method
        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # Find dataset
        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry = datasets_entry.value.find_nested_entry("uuid", dataset_uuid)[0]

        # Find current PE
        pes_entry = dataset_nested_entry.get_entry_by_name("process_events")
        pe_nested_entry = pes_entry.value.find_nested_entry("uuid", pe_uuid)[0]

        # The "pe_nested_entry" entry is a NestedEntry (return list of dict)
        if args["entry_format"] == "api":
            return pe_nested_entry.get_api_format()
        elif args["entry_format"] == "form":
            return pe_nested_entry.get_form_format()

    @token_required
    @api.expect(nested_study_entry_model_prop_id)
    def put(self, pe_uuid, study_id=None, dataset_uuid=None, user=None):
        """ Update a processing event for a given dataset """
        payload = api.payload

        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only pe_uuid
        if dataset_uuid is None:
            study_id, dataset_uuid = find_dataset_and_study_id_from_pe(
                pe_uuid = pe_uuid,
                prop_name_to_id = prop_name_to_id,
                prop_id_to_name = prop_id_to_name
            )
            if study_id is None or dataset_uuid is None:
                raise Exception(f"Processing event not found in any dataset (uuid = {pe_uuid})")

        # Used for helper route using only dataset_uuid
        if study_id is None:
            study_id = find_study_id_from_dataset(dataset_uuid, prop_name_to_id)
            if study_id is None:
                raise Exception(f"Dataset not found in any study (uuid = {dataset_uuid})")

        # 1. Split payload
        form_name = payload["form_name"]
        entries = payload["entries"]
        entry_format = payload.get("entry_format", "api")

        # 2. Get study data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # 3. Get dataset data
        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry = datasets_entry.value.find_nested_entry("uuid", dataset_uuid)[0]

        # 4. Get current processing event data
        pes_entry = dataset_nested_entry.get_entry_by_name("process_events")
        pe_nested_entry = pes_entry.value.find_nested_entry("uuid", pe_uuid)[0]
        pe_converter = FormatConverter(mapper=prop_id_to_name)
        pe_converter.entries = pe_nested_entry.value

        # 5. Get new processing event data
        if entry_format == "api":
            new_pe_converter = FormatConverter(mapper=prop_id_to_name)
            new_pe_converter.add_api_format(entries)
        elif entry_format == "form":
            new_pe_converter = FormatConverter(mapper=prop_name_to_id)
            new_pe_converter.add_form_format(entries)

        # 6. Clean new data and get entries to remove
        entries_to_remove = new_pe_converter.clean_data()

        # 7. Update current processing event by adding, updating and deleting entries
        pe_converter.add_or_update_entries(new_pe_converter.entries)
        pe_converter.remove_entries(entries=entries_to_remove)
        pe_nested_entry.value = pe_converter.entries

        # 8. Validate processing event data against form
        validate_form_format_against_form(form_name, pe_converter.get_form_format())

        # 9. Update study state, data and ulpoad on DB
        message = "Updated processing event"
        update_study(study, study_converter, payload, message, user)
        return {"message": message}

    @token_required
    def delete(self, pe_uuid, study_id=None, dataset_uuid=None, user=None):
        """ Delete a processing event given its unique identifier """
        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only pe_uuid
        if dataset_uuid is None:
            study_id, dataset_uuid = find_dataset_and_study_id_from_pe(
                pe_uuid = pe_uuid,
                prop_name_to_id = prop_name_to_id,
                prop_id_to_name = prop_id_to_name
            )
            if study_id is None or dataset_uuid is None:
                raise Exception(f"Processing event not found in any dataset (uuid = {pe_uuid})")

        # Used for helper route using only dataset_uuid
        if study_id is None:
            study_id = find_study_id_from_dataset(dataset_uuid, prop_name_to_id)
            if study_id is None:
                raise Exception(f"Dataset not found in any study (uuid = {dataset_uuid})")

        # 1. Get study data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # 2. Get dataset data
        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry = datasets_entry.value.find_nested_entry("uuid", dataset_uuid)[0]

        # 3. Delete specific processing event
        pes_entry = dataset_nested_entry.get_entry_by_name("process_events")
        pes_entry.value.delete_nested_entry("uuid", pe_uuid)

        if len(pes_entry.value.value) == 0:
            dataset_nested_entry.remove_entries(prop_names=["process_events"])

        # 4. Update study state, data and ulpoad on DB
        message = f"Deleted processing event"
        update_study(study, study_converter, api.payload, message, user)

        return {"message": message}


def find_study_id_from_dataset(dataset_uuid, prop_name_to_id):
    """ Find parent study given a dataset_uuid """
    study_id = None

    aggregated_studies = get_aggregated_studies_and_datasets(
        prop_map = prop_name_to_id,
        pes = False
    )

    for study in aggregated_studies:
        if dataset_uuid in study["datasets_uuids"]:
            return study["id"]

    return study_id


def find_dataset_and_study_id_from_pe(pe_uuid, prop_name_to_id, prop_id_to_name):
    """ Find parent study and dataset given a pe_uuid """
    study_id = None
    dataset_uuid = None

    aggregated_studies = get_aggregated_studies_and_datasets(
        prop_map = prop_name_to_id,
        pes = True
    )

    for potential_study in aggregated_studies:
        if pe_uuid in potential_study["pes_uuids"]:
            study = potential_study
            study_id = study["id"]
            break
    else:
        return study_id, dataset_uuid

    datasets_list_entry = NestedListEntry(FormatConverter(prop_id_to_name))\
        .add_api_format(study["datasets"])

    for dataset_nested_entry in datasets_list_entry.value:
        dataset_uuid = dataset_nested_entry.get_entry_by_name("uuid").value
        pes_entry = dataset_nested_entry.get_entry_by_name("process_events")

        try:
            pes_entry.value.find_nested_entry("uuid", pe_uuid)
            return study_id, dataset_uuid
        except:
            pass # Processing event not in this dataset

    return study_id, dataset_uuid

def get_aggregated_studies_and_datasets(prop_map, pes=False):
    """
    Super messy and dirty mongoDB aggregation to save time finding a study
    from a dataset_uuid.
    Note to future self: so sorry about that but no worry, Elastic Search will replace that.
    If pes = False, only datasets_uuids will be returned
    If pes = True, only datasets with at least one pe will be returned
    """
    # TODO: This should go away when we index all studies in form format with Elastic Search

    pipeline_datasets = [
        # Keep only datasets entry
        {"$addFields": {
            "datasets": {
                "$filter": {
                    "input":"$entries",
                    "as":"entry",
                    "cond":{"$eq": [{"$toString": "$$entry.property"}, prop_map["datasets"]]}
                }
            }
        }},

        # Keep studies with at least one dataset
        {"$match": {"datasets.0" : {"$exists" : True}}},

        # Take first (and only) element of filtered entries
        {"$addFields": {"datasets": {"$arrayElemAt": ["$datasets", 0]}}},
        # Get the actual list of datasets from the datasets entry value
        {"$addFields": {"datasets": "$datasets.value"}},

        # Dataset UUIDs: Keep only dataset_uuid entries (exactly 1)
        {"$addFields": {
            "datasets_uuids": {
                "$map": {
                    "input": "$datasets",
                    "as": "dataset",
                    "in": {
                        "$filter": {
                            "input": "$$dataset",
                            "as": "dataset_entry",
                            "cond":{"$eq": ["$$dataset_entry.property", prop_map["uuid"]]}
                        }
                    }
                }
            }
        }},

        # Dataset UUIDs: Take first (and only) element of filtered entries
        {"$addFields": {
            "datasets_uuids": {
                "$map": {
                    "input": "$datasets_uuids",
                    "as": "dataset",
                    "in": {"$arrayElemAt": ["$$dataset", 0]}
                }
            }
        }},

        # Dataset UUIDs: make a flat list of UUIDs
        {"$addFields": {
            "datasets_uuids": {
                "$map": {
                    "input": "$datasets_uuids",
                    "as": "uuid_entry",
                    "in": "$$uuid_entry.value"
                }
            }
        }}
    ]

    if pes == False:
        pipeline_datasets_format = [
            # Clean, project only wanted fields
            {"$project": {"id": {"$toString": "$_id"}, "datasets_uuids": 1, "datasets":1, "_id": 0}},
        ]
        pipeline = pipeline_datasets + pipeline_datasets_format
        aggregated_studies = Study.objects().aggregate(pipeline)

        return aggregated_studies

    else:
        pipeline_pes = [
            # Processing envents UUIDs: Keep only process_events entries (exactly 1)
            {"$addFields": {
                "datasets_for_pe": {
                    "$map": {
                        "input": "$datasets",
                        "as": "dataset",
                        "in": {
                            "$filter": {
                                "input": "$$dataset",
                                "as": "dataset_entry",
                                "cond":{"$eq": ["$$dataset_entry.property", prop_map["process_events"]]}
                            }
                        }
                    }
                }
            }},

            # Processing envents UUIDs: Take first (and only) element of filtered dataset entries
            {"$addFields": {
                "datasets_for_pe": {
                    "$map": {
                        "input": "$datasets_for_pe",
                        "as": "dataset",
                        "in": {"$arrayElemAt": ["$$dataset", 0]}
                    }
                }
            }},

            # Processing envents UUIDs: make a flat list of processing events
            {"$addFields": {
                "datasets_for_pe": {
                    "$map": {
                        "input": "$datasets_for_pe",
                        "as": "dataset",
                        "in": "$$dataset.value"
                    }
                }
            }},

            # Processing envents UUIDs: Keep only uuid entries (exactly 1)
            {"$addFields": {
                "datasets_for_pe": {
                    "$map": {
                        "input": "$datasets_for_pe",
                        "as": "dataset",
                        "in": {
                            "$map": {
                                "input": "$$dataset",
                                "as": "pe",
                                "in": {
                                    "$filter": {
                                        "input": "$$pe",
                                        "as": "pe_entry",
                                        "cond":{"$eq": ["$$pe_entry.property", prop_map["uuid"]]}
                                    }
                                }
                            }
                        }
                    }
                }
            }},

            # Processing envents UUIDs: Take first (and only) element of filtered entries
            {"$addFields": {
                "datasets_for_pe": {
                    "$map": {
                        "input": "$datasets_for_pe",
                        "as": "dataset",
                        "in": {
                            "$map": {
                                "input": "$$dataset",
                                "as": "pe",
                                "in": {"$arrayElemAt": ["$$pe", 0]}
                            }
                        }
                    }
                }
            }},

            # Processing envents UUIDs: make a flat list of UUIDs (per dataset)
            {"$addFields": {
                "pes_uuids": {
                    "$map": {
                        "input": "$datasets_for_pe",
                        "as": "dataset",
                        "in": {
                            "$map": {
                                "input": "$$dataset",
                                "as": "pe",
                                "in": "$$pe.value"
                            }
                        }
                    }
                }
            }},

            # Processing envents UUIDs: Flatten the UUID list (no separation per dataset)
            # It also removes the None but I have no idea why
            {"$unwind": "$pes_uuids"},
            {"$unwind": "$pes_uuids"},
            {"$unwind": "$datasets_uuids"},
            {"$unwind": "$datasets_uuids"},
            {"$unwind": "$datasets"},
            {"$group": {
                "_id": "$_id",
                "pes_uuids": {"$addToSet": "$pes_uuids"},
                "datasets_uuids": {"$addToSet": "$datasets_uuids"},
                "datasets": {"$addToSet": "$datasets"},
            }},

            # Clean, project only wanted fields
            {"$project": {"id": {"$toString": "$_id"}, "datasets_uuids": 1, "pes_uuids": 1, "datasets":1, "_id": 0}},
        ]
        pipeline = pipeline_datasets + pipeline_pes
        aggregated_studies = Study.objects().aggregate(pipeline)

        return aggregated_studies

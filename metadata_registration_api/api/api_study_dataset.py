from flask import current_app as app
from flask_restx import Namespace, Resource, marshal
from flask_restx import reqparse

from metadata_registration_lib.api_utils import (
    reverse_map,
    FormatConverter,
    Entry,
    NestedEntry,
    add_uuid_entry_if_missing,
    get_entity_converter,
    add_entity_to_study_nested_list,
)

from metadata_registration_api.api.api_utils import get_property_map
from .api_study import (
    entry_format_param,
    entry_model_prop_id,
    entry_model_form_format,
    study_model,
    nested_study_entry_model_prop_id,
)
from .api_study import validate_form_format_against_form, update_study
from .decorators import token_required
from ..model import Study
from ..mongo_utils import (
    find_study_id_from_lvl1_uuid,
    find_study_id_and_lvl1_uuid_from_lvl2_uuid,
)

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
        """Fetch a list of all datasets for a given study"""
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
        """Add a new dataset for a given study"""
        payload = api.payload

        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # 1. Split payload
        form_name = payload["form_name"]
        entries = payload["entries"]
        entry_format = payload.get("entry_format", "api")

        if entry_format == "form":
            prop_name_to_syns = get_property_map(key="name", value="synonyms")
        else:
            prop_name_to_syns = None

        # 2. Get study data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # 3. Create dataset entry and append it to "datasets"
        # Format and clean entity
        dataset_converter, _ = get_entity_converter(
            entries,
            entry_format,
            prop_id_to_name,
            prop_name_to_id,
            replace_synonyms=True,
            prop_name_to_syns=prop_name_to_syns,
        )
        # Generate UUID
        dataset_converter, dataset_uuid = add_uuid_entry_if_missing(
            dataset_converter, prop_name_to_id
        )

        # Sort entries according to form
        form_cls = app.form_manager.get_form_by_name(form_name=form_name)
        dataset_converter.sort_from_form(form_cls())

        study_converter = add_entity_to_study_nested_list(
            study_converter=study_converter,
            entity_converter=dataset_converter,
            prop_name_to_id=prop_name_to_id,
            study_list_prop="datasets",
        )

        # 4. Validate dataset data against form
        validate_form_format_against_form(
            form_name, dataset_converter.get_form_format(), form_cls=form_cls
        )

        # 5. Update study state, data and upload on DB
        message = "Added dataset"
        update_study(study, study_converter, payload, message, user)
        return {"message": message, "uuid": dataset_uuid}, 201


@api.route("/id/<study_id>/datasets/id/<dataset_uuid>", strict_slashes=False)
@api.route(
    "/datasets/id/<dataset_uuid>",
    strict_slashes=False,
    doc={"description": "Alias route for a specific dataset without study_id"},
)
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
        """Fetch a specific dataset for a given study"""
        args = self._get_parser.parse_args()

        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only dataset_uuid
        if study_id is None:
            study_id = find_study_id_from_lvl1_uuid(
                "dataset", dataset_uuid, prop_name_to_id
            )
            if study_id is None:
                raise Exception(
                    f"Dataset not found in any study (uuid = {dataset_uuid})"
                )

        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        # The converter is used for its get_entry_by_name() method
        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry = datasets_entry.value.find_nested_entry(
            "uuid", dataset_uuid
        )[0]

        # The "dataset_nested_entry" entry is a NestedEntry (return list of dict)
        if args["entry_format"] == "api":
            return dataset_nested_entry.get_api_format()
        elif args["entry_format"] == "form":
            return dataset_nested_entry.get_form_format()

    @token_required
    @api.expect(nested_study_entry_model_prop_id)
    def put(self, dataset_uuid, study_id=None, user=None):
        """Update a dataset for a given study"""
        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only dataset_uuid
        if study_id is None:
            study_id = find_study_id_from_lvl1_uuid(
                "dataset", dataset_uuid, prop_name_to_id
            )
            if study_id is None:
                raise Exception(
                    f"Dataset not found in any study (uuid = {dataset_uuid})"
                )

        payload = api.payload

        # 1. Split payload
        form_name = payload["form_name"]
        entries = payload["entries"]
        entry_format = payload.get("entry_format", "api")

        if entry_format == "form":
            prop_name_to_syns = get_property_map(key="name", value="synonyms")
        else:
            prop_name_to_syns = None

        # 2. Get study data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # 3. Get current dataset data
        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry = datasets_entry.value.find_nested_entry(
            "uuid", dataset_uuid
        )[0]
        dataset_converter = FormatConverter(mapper=prop_id_to_name)
        dataset_converter.entries = dataset_nested_entry.value

        # 4. Get new dataset data and get entries to remove
        new_dataset_converter, entries_to_remove = get_entity_converter(
            entries,
            entry_format,
            prop_id_to_name,
            prop_name_to_id,
            replace_synonyms=True,
            prop_name_to_syns=prop_name_to_syns,
        )

        # 5. Update current dataset by adding, updating and deleting entries
        # Nested entries not present in the original form are ignored (example: dataset["samples"])
        # won't be deleted if not present in the new data), it needs to be None or "" to be deleted
        dataset_converter.add_or_update_entries(new_dataset_converter.entries)
        dataset_converter.remove_entries(entries=entries_to_remove)

        # Sort entries according to form
        form_cls = app.form_manager.get_form_by_name(form_name=form_name)
        dataset_converter.sort_from_form(form_cls())

        # 6. Validate dataset data against form
        validate_form_format_against_form(
            form_name, dataset_converter.get_form_format(), form_cls=form_cls
        )

        dataset_nested_entry.value = dataset_converter.entries

        # 7. Update study state, data and upload on DB
        message = "Updated dataset"
        update_study(study, study_converter, payload, message, user)
        return {"message": message}

    @token_required
    def delete(self, dataset_uuid, study_id=None, user=None):
        """Delete a dataset from a study given its unique identifier"""
        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only dataset_uuid
        if study_id is None:
            study_id = find_study_id_from_lvl1_uuid(
                "dataset", dataset_uuid, prop_name_to_id
            )
            if study_id is None:
                raise Exception(
                    f"Dataset not found in any study (uuid = {dataset_uuid})"
                )

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

        # 3. Update study state, data and upload on DB
        message = f"Deleted dataset"
        update_study(study, study_converter, api.payload, message, user)

        return {"message": message}


@api.route("/id/<study_id>/datasets/id/<dataset_uuid>/pes")
@api.route(
    "/datasets/id/<dataset_uuid>/pes",
    doc={"description": "Alias route for a dataset's PEs without study_id"},
)
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
        """Fetch a list of all processing events for a given study"""
        args = self._get_parser.parse_args()

        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only dataset_uuid
        if study_id is None:
            study_id = find_study_id_from_lvl1_uuid(
                "dataset", dataset_uuid, prop_name_to_id
            )
            if study_id is None:
                raise Exception(
                    f"Dataset not found in any study (uuid = {dataset_uuid})"
                )

        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        # The converter is used for its get_entry_by_name() method
        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # Find dataset
        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry = datasets_entry.value.find_nested_entry(
            "uuid", dataset_uuid
        )[0]

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
        """Add a new processing event for a given dataset"""
        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only dataset_uuid
        if study_id is None:
            study_id = find_study_id_from_lvl1_uuid(
                "dataset", dataset_uuid, prop_name_to_id
            )
            if study_id is None:
                raise Exception(
                    f"Dataset not found in any study (uuid = {dataset_uuid})"
                )

        payload = api.payload

        # 1. Split payload
        form_name = payload["form_name"]
        entries = payload["entries"]
        entry_format = payload.get("entry_format", "api")

        if entry_format == "form":
            prop_name_to_syns = get_property_map(key="name", value="synonyms")
        else:
            prop_name_to_syns = None

        # 2. Get study and dataset data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)
        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])
        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry, dataset_position = datasets_entry.value.find_nested_entry(
            "uuid", dataset_uuid
        )

        # 3. Format and clean processing event data
        pe_converter, _ = get_entity_converter(
            entries,
            entry_format,
            prop_id_to_name,
            prop_name_to_id,
            replace_synonyms=True,
            prop_name_to_syns=prop_name_to_syns,
        )

        # 4. Generate UUID
        pe_converter, pe_uuid = add_uuid_entry_if_missing(
            pe_converter, prop_name_to_id, replace=False
        )

        # Sort entries according to form
        form_cls = app.form_manager.get_form_by_name(form_name=form_name)
        pe_converter.sort_from_form(form_cls())

        pe_nested_entry = NestedEntry(pe_converter)
        pe_nested_entry.value = pe_converter.entries

        # 5. Check if "process_events"" entry already exist study, creates it if it doesn't
        pes_entry = dataset_nested_entry.get_entry_by_name("process_events")

        if pes_entry is not None:
            pes_entry.value.value.append(pe_nested_entry)
        else:
            pes_entry = Entry(FormatConverter(prop_name_to_id)).add_form_format(
                "process_events", [pe_nested_entry.get_form_format()]
            )
            dataset_nested_entry.value.append(pes_entry)

        datasets_entry.value.value[dataset_position] = dataset_nested_entry

        # 6. Validate processing data against form
        validate_form_format_against_form(
            form_name, pe_converter.get_form_format(), form_cls=form_cls
        )

        # 7. Update study state, data and upload on DB
        message = "Added processing event"
        update_study(study, study_converter, payload, message, user)
        return {"message": message, "uuid": pe_uuid}, 201


@api.route(
    "/id/<study_id>/datasets/id/<dataset_uuid>/pes/id/<pe_uuid>", strict_slashes=False
)
@api.route(
    "/pes/id/<pe_uuid>",
    strict_slashes=False,
    doc={
        "description": "Alias route for a specific PE without study_id or dataset_uuid"
    },
)
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
        """Fetch a specific processing for a given dataset"""
        args = self._get_parser.parse_args()

        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only pe_uuid
        if dataset_uuid is None:
            study_id, dataset_uuid = find_study_id_and_lvl1_uuid_from_lvl2_uuid(
                lvl1_prop="dataset",
                lvl2_prop="process_event",
                lvl2_uuid=pe_uuid,
                prop_name_to_id=prop_name_to_id,
                prop_id_to_name=prop_id_to_name,
            )
            if study_id is None or dataset_uuid is None:
                raise Exception(
                    f"Processing event not found in any dataset (uuid = {pe_uuid})"
                )

        # Used for helper route using only dataset_uuid
        if study_id is None:
            study_id = find_study_id_from_lvl1_uuid(
                "dataset", dataset_uuid, prop_name_to_id
            )
            if study_id is None:
                raise Exception(
                    f"Dataset not found in any study (uuid = {dataset_uuid})"
                )

        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        # The converter is used for its get_entry_by_name() method
        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # Find dataset
        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry = datasets_entry.value.find_nested_entry(
            "uuid", dataset_uuid
        )[0]

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
        """Update a processing event for a given dataset"""
        payload = api.payload

        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only pe_uuid
        if dataset_uuid is None:
            study_id, dataset_uuid = find_study_id_and_lvl1_uuid_from_lvl2_uuid(
                lvl1_prop="dataset",
                lvl2_prop="process_event",
                lvl2_uuid=pe_uuid,
                prop_name_to_id=prop_name_to_id,
                prop_id_to_name=prop_id_to_name,
            )
            if study_id is None or dataset_uuid is None:
                raise Exception(
                    f"Processing event not found in any dataset (uuid = {pe_uuid})"
                )

        # Used for helper route using only dataset_uuid
        if study_id is None:
            study_id = find_study_id_from_lvl1_uuid(
                "dataset", dataset_uuid, prop_name_to_id
            )
            if study_id is None:
                raise Exception(
                    f"Dataset not found in any study (uuid = {dataset_uuid})"
                )

        # 1. Split payload
        form_name = payload["form_name"]
        entries = payload["entries"]
        entry_format = payload.get("entry_format", "api")

        if entry_format == "form":
            prop_name_to_syns = get_property_map(key="name", value="synonyms")
        else:
            prop_name_to_syns = None

        # 2. Get study data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # 3. Get dataset data
        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry = datasets_entry.value.find_nested_entry(
            "uuid", dataset_uuid
        )[0]

        # 4. Get current processing event data
        pes_entry = dataset_nested_entry.get_entry_by_name("process_events")
        pe_nested_entry = pes_entry.value.find_nested_entry("uuid", pe_uuid)[0]
        pe_converter = FormatConverter(mapper=prop_id_to_name)
        pe_converter.entries = pe_nested_entry.value

        # 5. Get new processing event data
        new_pe_converter, entries_to_remove = get_entity_converter(
            entries,
            entry_format,
            prop_id_to_name,
            prop_name_to_id,
            replace_synonyms=True,
            prop_name_to_syns=prop_name_to_syns,
        )

        # 6. Update current processing event by adding, updating and deleting entries
        # Nested entries not present in the original form are ignored (example: pe["results"])
        # won't be deleted if not present in the new data), it needs to be None or "" to be deleted
        pe_converter.add_or_update_entries(new_pe_converter.entries)
        pe_converter.remove_entries(entries=entries_to_remove)

        # Sort entries according to form
        form_cls = app.form_manager.get_form_by_name(form_name=form_name)
        pe_converter.sort_from_form(form_cls())

        pe_nested_entry.value = pe_converter.entries

        # 7. Validate processing event data against form
        validate_form_format_against_form(
            form_name, pe_converter.get_form_format(), form_cls=form_cls
        )

        # 8. Update study state, data and upload on DB
        message = "Updated processing event"
        update_study(study, study_converter, payload, message, user)
        return {"message": message}

    @token_required
    def delete(self, pe_uuid, study_id=None, dataset_uuid=None, user=None):
        """Delete a processing event given its unique identifier"""
        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only pe_uuid
        if dataset_uuid is None:
            study_id, dataset_uuid = find_study_id_and_lvl1_uuid_from_lvl2_uuid(
                lvl1_prop="dataset",
                lvl2_prop="process_event",
                lvl2_uuid=pe_uuid,
                prop_name_to_id=prop_name_to_id,
                prop_id_to_name=prop_id_to_name,
            )
            if study_id is None or dataset_uuid is None:
                raise Exception(
                    f"Processing event not found in any dataset (uuid = {pe_uuid})"
                )

        # Used for helper route using only dataset_uuid
        if study_id is None:
            study_id = find_study_id_from_lvl1_uuid(
                "dataset", dataset_uuid, prop_name_to_id
            )
            if study_id is None:
                raise Exception(
                    f"Dataset not found in any study (uuid = {dataset_uuid})"
                )

        # 1. Get study data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # 2. Get dataset data
        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry = datasets_entry.value.find_nested_entry(
            "uuid", dataset_uuid
        )[0]

        # 3. Delete specific processing event
        pes_entry = dataset_nested_entry.get_entry_by_name("process_events")
        pes_entry.value.delete_nested_entry("uuid", pe_uuid)

        if len(pes_entry.value.value) == 0:
            dataset_nested_entry.remove_entries(prop_names=["process_events"])

        # 4. Update study state, data and upload on DB
        message = f"Deleted processing event"
        update_study(study, study_converter, api.payload, message, user)

        return {"message": message}

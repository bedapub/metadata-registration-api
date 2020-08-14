import os
from datetime import datetime
from urllib.parse import urljoin
import uuid

from flask import current_app as app
from flask_restx import Namespace, Resource, fields, marshal
from flask_restx import reqparse, inputs

from metadata_registration_lib.api_utils import (FormatConverter, map_key_value,
    Entry, NestedEntry)
from metadata_registration_api.api.api_utils import MetaInformation, ChangeLog
from .api_props import property_model_id
from .decorators import token_required
from ..errors import IdenticalPropertyException, RequestBodyException
from ..model import Study

api = Namespace("Studies", description="Study related operations")

# Model definition
# ----------------------------------------------------------------------------------------------------------------------

entry_model = api.model("Entry", {
    "property": fields.Nested(property_model_id),
    "value": fields.Raw()
})

change_log = api.model("Change Log", {
    "user_id": fields.String(),
    "manual_user": fields.String(),
    "action": fields.String(),
    "timestamp": fields.DateTime()
})

meta_information_model = api.model("Metadata Information", {
    "state": fields.String(),
    "deprecated": fields.Boolean(),
    "change_log": fields.List(fields.Nested(change_log))
})

study_model = api.model("Study", {
    "entries": fields.List(fields.Nested(entry_model)),
    "meta_information": fields.Nested(meta_information_model),
})

study_model_id = api.inherit("Study with id", study_model, {
    "id": fields.String()
})

field_add_model = api.model("Add Field", {
    "property": fields.String(example="Property Object Id"),
    "value": fields.Raw()
})

study_add_model = api.model("Add Study", {
    "form_name": fields.String(example="Form Object Id", required=True),
    "initial_state": fields.String(default="generic_state", required=True, description="The initial state name"),
    "entries": fields.List(fields.Nested(field_add_model)),
    "manual_meta_information": fields.Raw()
})

study_modify_model = api.inherit("Modify study model", study_add_model, {
    "id": fields.String()
})

nested_study_entry_add_modify_model = api.model("Add or modify a nested study entry", {
    "entries": fields.List(fields.Nested(entry_model)),
    "form_name": fields.String(example="Form name for validation", required=True),
    "manual_meta_information": fields.Raw()
})

# Routes
# ----------------------------------------------------------------------------------------------------------------------

@api.route("")
class ApiStudy(Resource):
    _delete_parser = reqparse.RequestParser()
    _delete_parser.add_argument("complete",
                                type=inputs.boolean,
                                default=False,
                                help="Boolean indicator to remove an entry instead of deprecating it (cannot be undone)"
                                )

    _get_parser = reqparse.RequestParser()
    _get_parser.add_argument(
        "deprecated",
        type=inputs.boolean,
        location="args",
        default=False,
        help="Boolean indicator which determines if deprecated entries should be returned as well",
    )
    _get_parser.add_argument(
        "skip",
        type=int,
        location="args",
        default=0,
        help="Number of results which should be skipped"
    )

    _get_parser.add_argument(
        "limit",
        type=int,
        location="args",
        default=100,
        help="Number of results which should be returned"
    )

    # @token_required
    @api.marshal_with(study_model_id)
    @api.expect(parser=_get_parser)
    def get(self):
        """ Fetch a list with all entries """
        # Convert query parameters
        args = self._get_parser.parse_args()
        include_deprecate = args["deprecated"]

        res = Study.objects.skip(args["skip"])

        # Issue with limit(0) that returns 0 items instead of all of them
        if args["limit"] != 0:
            res = res.limit(args["limit"])

        if not include_deprecate:
            res = res.filter(meta_information__deprecated=False)

        return list(res.select_related())

    @token_required
    @api.expect(study_add_model)
    def post(self, user=None):
        """ Add a new entry """

        payload = api.payload

        # 1. Split payload
        form_name = payload["form_name"]
        initial_state = payload["initial_state"]
        entries = payload["entries"]

        form_cls = app.form_manager.get_form_by_name(form_name=form_name)

        if initial_state == "rna_sequencing_biokit":
            initial_state = "BiokitUploadState"

        app.study_state_machine.load_state(name=initial_state)

        # 2. Convert submitted data into form compatible format

        try:
            if len(entries) != len({prop["property"] for prop in entries}):
                raise IdenticalPropertyException("The entries cannot have several identical property values.")
        except TypeError as e:
            raise RequestBodyException("Entries has wrong format.") from e

        form_data_json = validate_against_form(form_cls, form_name, entries)

        # 4. Evaluate new state of study by passing form data
        app.study_state_machine.create_study(**form_data_json)
        state = app.study_state_machine.current_state

        meta_info = MetaInformation(state=str(state))
        log = ChangeLog(user_id=user.id if user else None,
                        action="Created study",
                        timestamp=datetime.now(),
                        manual_user=payload.get("manual_meta_information", {}).get("user", None))
        meta_info.add_log(log)

        entry_data = {"entries": entries, "meta_information": meta_info.to_json()}

        # 6. Insert data into database
        entry = Study(**entry_data)
        entry.save()
        return {"message": f"Study added", "id": str(entry.id)}, 201


    @token_required
    @api.expect(parser=_delete_parser)
    def delete(self, user=None):
        """ Deprecates all entries """

        parser = reqparse.RequestParser()
        parser.add_argument("complete", type=inputs.boolean, default=False)
        args = parser.parse_args()

        force_delete = args["complete"]

        entry = Study.objects().all()
        # if not force_delete:
        #     entry.update(deprecated=True)
        #     return {"message": "Deprecate all entries"}
        # else:
        entry.delete()
        return {"message": "Delete all entries"}


@api.route("/id/<id>", strict_slashes=False)
@api.param("id", "The property identifier")
class ApiStudy(Resource):
    _delete_parser = reqparse.RequestParser()
    _delete_parser.add_argument("complete",
                               type=inputs.boolean,
                               default=False,
                               help="Boolean indicator to remove an entry instead of deprecating it (cannot be undone)"
                               )

    # @token_required
    @api.marshal_with(study_model_id)
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        return Study.objects(id=id).get()

    @token_required
    @api.expect(study_modify_model)
    def put(self, id, user=None):
        """ Update an entry given its unique identifier """

        payload = api.payload

        # 1. Split payload
        study_id = id
        form_name = payload["form_name"]
        entries = payload["entries"]

        entry = Study.objects(id=study_id).first()

        # 1. Extract form name and create form from FormManager
        form_cls = app.form_manager.get_form_by_name(form_name=form_name)

        # 2. Convert submitted data in form format
        form_data_json = validate_against_form(form_cls, form_name, entries)
        # 4. Determine current state and evaluate next state
        state_name = str(entry.meta_information.state)

        if state_name == "rna_sequencing_biokit":
            state_name = "BiokitUploadState"

        app.study_state_machine.load_state(name=state_name)
        app.study_state_machine.change_state(**form_data_json)
        new_state = app.study_state_machine.current_state

        # 5. Update metadata
        # 5. Create and append meta information to the entry
        meta_info = MetaInformation(
            state=state_name,
            change_log=entry.meta_information.change_log
        )

        log = ChangeLog(action="Updated study",
                        user_id=user.id if user else None,
                        timestamp=datetime.now(),
                        manual_user=payload.get("manual_meta_information", {}).get("user", None))
        meta_info.state = str(new_state)
        meta_info.add_log(log)

        entry_data = {"entries": entries, "meta_information": meta_info.to_json()}

        # 6. Update data in database
        entry.update(**entry_data)
        return {"message": f"Update entry"}

    @token_required
    @api.expect(parser=_delete_parser)
    def delete(self, id, user=None):
        """ Delete an entry given its unique identifier """
        args = self._delete_parser.parse_args()
        force_delete = args["complete"]

        entry = Study.objects(id=id).get()
        if not force_delete:
            entry.update(meta_information__deprecated=True)
            return {"message": "Deprecate entry"}
        else:
            entry.delete()
            return {"message": "Delete entry"}


@api.route("/id/<study_id>/datasets")
@api.param("study_id", "The study identifier")
class ApiStudyDataset(Resource):
    _get_parser = reqparse.RequestParser()

    # @token_required
    @api.expect(parser=_get_parser)
    def get(self, study_id):
        """ Fetch a list of all datasets for a given study """
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        prop_map = get_property_map(key="id", value="name")

        # The converter is used for its get_entry_by_name() method
        study_converter = FormatConverter(mapper=prop_map)
        study_converter.add_api_format(study_json["entries"])

        datasets_entry = study_converter.get_entry_by_name("datasets")

        if datasets_entry is not None:
            # The "datasets" entry is a NestedListEntry (return list of list)
            return datasets_entry.get_api_format()
        else:
            return []

    @token_required
    @api.expect(nested_study_entry_add_modify_model)
    def post(self, study_id, user=None):
        """ Add a new dataset for a given study """
        payload = api.payload

        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = get_property_map(key="name", value="id")

        # 1. Split payload
        form_name = payload["form_name"]
        entries = payload["entries"]

        # 2. Get study data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # 3. Generate UUID
        dataset_uuid = str(uuid.uuid1())
        entries.insert(0, {"property": prop_name_to_id["uuid"], "value": dataset_uuid})

        # 4. Format and clean dataset data
        dataset_converter = FormatConverter(mapper=prop_id_to_name)
        dataset_converter.add_api_format(entries)
        dataset_converter.clean_data()
        dataset_nested_entry = NestedEntry(dataset_converter)
        dataset_nested_entry.value = dataset_converter.entries

        # 5. Check if "datasets" entry already exist study, creates it if it doesn't
        datasets_entry = study_converter.get_entry_by_name("datasets")

        if datasets_entry is not None:
            datasets_entry.value.value.append(dataset_nested_entry)
        else:
            datasets_entry = Entry(dataset_converter).add_api_format({
                "property": prop_name_to_id["datasets"],
                "value": [dataset_nested_entry.get_api_format()]
            })
            study_converter.entries.append(datasets_entry)

        # 6. Validate dataset data against form
        validate_form_format_against_form(form_name, dataset_converter.get_form_format())

        # 7. Update study state, data and ulpoad on DB
        message = "Added dataset"
        update_study(study, study_converter, payload, message, user)
        return {"message": message, "uuid": dataset_uuid}, 201


@api.route("/id/<study_id>/datasets/id/<dataset_uuid>", strict_slashes=False)
@api.param("study_id", "The study identifier")
@api.param("dataset_uuid", "The dataset identifier")
class ApiStudyDataset(Resource):

    # @token_required
    def get(self, study_id, dataset_uuid):
        """ Fetch a specific dataset for a given study """
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        prop_map = get_property_map(key="id", value="name")

        # The converter is used for its get_entry_by_name() method
        study_converter = FormatConverter(mapper=prop_map)
        study_converter.add_api_format(study_json["entries"])

        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry = datasets_entry.value.find_nested_entry("uuid", dataset_uuid)[0]

        # The "dataset_nested_entry" entry is a NestedEntry (return list of dict)
        return dataset_nested_entry.get_api_format()

    @token_required
    @api.expect(nested_study_entry_add_modify_model)
    def put(self, study_id, dataset_uuid, user=None):
        """ Update a dataset for a given study """
        payload = api.payload

        prop_id_to_name = get_property_map(key="id", value="name")

        # 1. Split payload
        form_name = payload["form_name"]
        entries = payload["entries"]

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
        new_dataset_converter = FormatConverter(mapper=prop_id_to_name)
        new_dataset_converter.add_api_format(entries)

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


@api.route("/id/<study_id>/datasets/id/<dataset_uuid>/pes")
@api.param("study_id", "The study identifier")
@api.param("dataset_uuid", "The dataset identifier")
class ApiStudyPE(Resource):
    _get_parser = reqparse.RequestParser()

    # @token_required
    @api.expect(parser=_get_parser)
    def get(self, study_id, dataset_uuid):
        """ Fetch a list of all processing events for a given study """
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        prop_map = get_property_map(key="id", value="name")

        # The converter is used for its get_entry_by_name() method
        study_converter = FormatConverter(mapper=prop_map)
        study_converter.add_api_format(study_json["entries"])

        # Find dataset
        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry = datasets_entry.value.find_nested_entry("uuid", dataset_uuid)[0]

        # Find PEs
        pes_entry = dataset_nested_entry.get_entry_by_name("process_events")

        if pes_entry is not None:
            # The "process_events" entry is a NestedListEntry (return list of list)
            return pes_entry.get_api_format()
        else:
            return []

    @token_required
    @api.expect(nested_study_entry_add_modify_model)
    def post(self, study_id, dataset_uuid, user=None):
        """ Add a new processing event for a given dataset """
        payload = api.payload

        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = get_property_map(key="name", value="id")

        # 1. Split payload
        form_name = payload["form_name"]
        entries = payload["entries"]

        # 2. Get study and dataset data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)
        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])
        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry, dataset_position = datasets_entry.value.find_nested_entry("uuid", dataset_uuid)

        # 3. Generate UUID
        pe_uuid = str(uuid.uuid1())
        entries.insert(0, {"property": prop_name_to_id["uuid"], "value": pe_uuid})

        # 4. Format and clean processing event data
        pe_converter = FormatConverter(mapper=prop_id_to_name)
        pe_converter.add_api_format(entries)
        pe_converter.clean_data()
        pe_nested_entry = NestedEntry(pe_converter)
        pe_nested_entry.value = pe_converter.entries

        # 5. Check if "process_events"" entry already exist study, creates it if it doesn't
        pes_entry = dataset_nested_entry.get_entry_by_name("process_events")

        if pes_entry is not None:
            pes_entry.value.value.append(pe_nested_entry)
        else:
            pes_entry = Entry(pe_converter).add_api_format({
                "property": prop_name_to_id["process_events"],
                "value": [pe_nested_entry.get_api_format()]
            })
            dataset_nested_entry.value.append(pes_entry)

        datasets_entry.value.value[dataset_position] = dataset_nested_entry

        # 6. Validate processing data against form
        validate_form_format_against_form(form_name, pe_converter.get_form_format())

        # 7. Update study state, data and ulpoad on DB
        message = "Added processing event"
        update_study(study, study_converter, payload, message, user)
        return {"message": message, "uuid": pe_uuid}, 201


@api.route("/id/<study_id>/datasets/id/<dataset_uuid>/pes/id/<pe_uuid>", strict_slashes=False)
@api.param("study_id", "The study identifier")
@api.param("dataset_uuid", "The dataset identifier")
@api.param("pe_uuid", "The processing event identifier")
class ApiStudyPE(Resource):

    # @token_required
    def get(self, study_id, dataset_uuid, pe_uuid):
        """ Fetch a specific processing for a given dataset """
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        prop_map =get_property_map(key="id", value="name")

        # The converter is used for its get_entry_by_name() method
        study_converter = FormatConverter(mapper=prop_map)
        study_converter.add_api_format(study_json["entries"])

        # Find dataset
        datasets_entry = study_converter.get_entry_by_name("datasets")
        dataset_nested_entry = datasets_entry.value.find_nested_entry("uuid", dataset_uuid)[0]

        # Find current PE
        pes_entry = dataset_nested_entry.get_entry_by_name("process_events")
        pe_nested_entry = pes_entry.value.find_nested_entry("uuid", pe_uuid)[0]

        # The "pe_nested_entry" entry is a NestedEntry (return list of dict)
        return pe_nested_entry.get_api_format()

    @token_required
    @api.expect(nested_study_entry_add_modify_model)
    def put(self, study_id, dataset_uuid, pe_uuid, user=None):
        """ Update a processing event for a given dataset """
        payload = api.payload

        prop_id_to_name = get_property_map(key="id", value="name")

        # 1. Split payload
        form_name = payload["form_name"]
        entries = payload["entries"]

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
        new_pe_converter = FormatConverter(mapper=prop_id_to_name)
        new_pe_converter.add_api_format(entries)

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


def validate_against_form(form_cls, form_name, entries):
    prop_map = get_property_map(key="id", value="name")

    form_data_json = FormatConverter(mapper=prop_map).add_api_format(entries).get_form_format()

    # 3. Validate data against form
    form_instance = form_cls()
    form_instance.process(data=form_data_json)

    if not form_instance.validate():
        raise RequestBodyException(f"Passed data did not validate with the form {form_name}: {form_instance.errors}")

    return form_data_json

def validate_form_format_against_form(form_name, form_data):
    form_cls = app.form_manager.get_form_by_name(form_name=form_name)
    form_instance = form_cls()
    form_instance.process(data=form_data)

    if not form_instance.validate():
        raise RequestBodyException(f"Passed data did not validate with the form {form_name}: {form_instance.errors}")

def get_property_map(key, value):
    """ Helper to get property mapper """
    property_url = urljoin(app.config["URL"], os.environ["API_EP_PROPERTY"])
    property_map = map_key_value(url=property_url, key=key, value=value)
    return property_map

def update_study(study, study_converter, payload, message, user=None):
    """ Steps to update study state, metadata and upload to DB """
    # 1. Determine current state and evaluate next state
    state_name = str(study.meta_information.state)

    app.study_state_machine.load_state(name=state_name)
    app.study_state_machine.change_state(**study_converter.get_form_format())
    new_state = app.study_state_machine.current_state

    # 2. Update metadata / Create and append meta information to the study
    meta_info = MetaInformation(
        state=state_name,
        change_log=study.meta_information.change_log
    )

    log = ChangeLog(action=message,
                    user_id=user.id if user else None,
                    timestamp=datetime.now(),
                    manual_user=payload.get("manual_meta_information", {}).get("user", None))
    meta_info.state = str(new_state)
    meta_info.add_log(log)

    study_data = {
        "entries": study_converter.get_api_format(),
        "meta_information": meta_info.to_json()
    }

    # 3. Update data in database
    study.update(**study_data)
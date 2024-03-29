from flask import current_app as app
from flask_restx import Namespace, Resource, marshal, fields
from flask_restx import reqparse

from metadata_registration_lib.api_utils import (
    reverse_map,
    FormatConverter,
    add_uuid_entry_if_missing,
    get_entity_converter,
    add_entity_to_study_nested_list,
)

from metadata_registration_lib.sample_utils import (
    unify_sample_entities_uuids,
    validate_sample_against_form,
)

from metadata_registration_api.api.api_utils import get_property_map
from .api_study import (
    entry_format_param,
    entry_model_prop_id,
    entry_model_form_format,
    study_model,
)
from .api_study import update_study
from .api_study_dataset import find_study_id_from_lvl1_uuid
from .decorators import token_required
from ..model import Study

api = Namespace("Samples", description="Sample related operations")

# Models and parser params
# ----------------------------------------------------------------------------------------------------------------------
def get_validate_field(text):
    return fields.Boolean(default=False, description=f"Validate {text}")


def get_form_name_field(default, text):
    return fields.String(
        default=default, description=f"Form used for {text} validation"
    )


sample_entries = fields.List(fields.Nested(entry_model_prop_id))

# form_names and validate keys need to match step names in LIB
sample_model_payload = api.model(
    "Add Sample",
    {
        "entries": sample_entries,
        "entry_format": fields.String(
            example="api", description="Format used for entries (api or form)"
        ),
        "validate": fields.Nested(
            api.model(
                "Validate flags",
                {
                    "treatment_ind": get_validate_field("Treatments on Individuals"),
                    "individual": get_validate_field("Individuals"),
                    "treatment_sam": get_validate_field("Treatments on Samples"),
                    "sample": get_validate_field("Samples"),
                },
            )
        ),
        "form_names": fields.Nested(
            api.model(
                "Form names",
                {
                    "treatment_ind": get_form_name_field(
                        "treatment", "Treatments on Individuals"
                    ),
                    "individual": get_form_name_field("individual", "Individuals"),
                    "treatment_sam": get_form_name_field(
                        "treatment", "Treatments on Samples"
                    ),
                    "sample": get_form_name_field("sample", "Samples"),
                },
            )
        ),
        "manual_meta_information": fields.Raw(),
    },
)

samples_model_payload = api.inherit(
    "Add/Replace Samples",
    sample_model_payload,
    {
        "entries": fields.List(sample_entries),
        "replace": fields.Boolean(
            default=False, description=f"Replace existing samples"
        ),
    },
)


# Routes
# ----------------------------------------------------------------------------------------------------------------------


@api.route("/id/<study_id>/samples/multiple")
@api.param("study_id", "The study identifier")
class ApiStudySamples(Resource):
    @token_required
    @api.expect(samples_model_payload)
    def post(self, study_id, user=None):
        """Add multiple new samples for a given study"""
        payload = api.payload

        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # 1. Split payload
        entries_list = payload["entries"]
        entry_format = payload.get("entry_format", "api")
        replace = payload.get("replace", False)
        validate_dict, forms = get_samples_validation_forms(payload)

        if entry_format == "form":
            prop_name_to_syns = get_property_map(key="name", value="synonyms")
        else:
            prop_name_to_syns = None

        # 2. Get study data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # 3. Unify UUIDs with existing entities (including nested ones)
        new_samples_form_format = []
        for entries in entries_list:
            # Format and clean entity
            sample_converter, _ = get_entity_converter(
                entries,
                entry_format,
                prop_id_to_name,
                prop_name_to_id,
                replace_synonyms=True,
                prop_name_to_syns=prop_name_to_syns,
            )
            new_samples_form_format.append(sample_converter.get_form_format())

        new_samples_form_format = unify_sample_entities_uuids(
            existing_samples=study_converter.get_form_format().get("samples", []),
            new_samples=new_samples_form_format,
        )

        # 4. Append new samples to "samples" in study
        if replace:
            study_converter.remove_entries(prop_names=["samples"])

        sample_uuids = []
        for sample_form_format in new_samples_form_format:
            # Format and clean entity
            sample_converter, _ = get_entity_converter(
                entries=sample_form_format,
                entry_format="form",
                prop_id_to_name=None,
                prop_name_to_id=prop_name_to_id,
                replace_synonyms=False,
            )

            # Generate UUID (redundant, UUIDs already generated by unify_sample_entities_uuids)
            sample_converter, sample_uuid = add_uuid_entry_if_missing(
                sample_converter, prop_name_to_id
            )

            study_converter = add_entity_to_study_nested_list(
                study_converter=study_converter,
                entity_converter=sample_converter,
                prop_name_to_id=prop_name_to_id,
                study_list_prop="samples",
            )

            sample_uuids.append(sample_uuid)

            # 5. Validate data against form
            validate_sample_against_form(
                sample_converter.get_form_format(), validate_dict, forms
            )

        # 6. Check unicity of specified properties
        check_samples_unicity(study_converter.get_form_format()["samples"])
        custom_sample_validation(study_converter.get_form_format()["samples"])

        # 7. Update study state, data and upload on DB
        message = f"Added {len(sample_uuids)} samples (replace = {replace})"
        update_study(study, study_converter, payload, message, user)
        return {"message": message, "uuids": sample_uuids}, 201


@api.route("/id/<study_id>/samples")
@api.param("study_id", "The study identifier")
class ApiStudySample(Resource):
    _get_parser = reqparse.RequestParser()
    _get_parser.add_argument("entry_format", **entry_format_param)

    _delete_parser = reqparse.RequestParser()
    _delete_parser.add_argument(
        "sample_uuids",
        action="append",
        help="Sample UUIDs to be deleted",
    )

    @token_required
    @api.response("200 - api", "Success (API format)", [[entry_model_prop_id]])
    @api.response("200 - form", "Success (form format)", [entry_model_form_format])
    @api.doc(parser=_get_parser)
    def get(self, study_id, user=None):
        """Fetch a list of all samples for a given study"""
        args = self._get_parser.parse_args()

        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        prop_map = get_property_map(key="id", value="name")

        # The converter is used for its get_entry_by_name() method
        study_converter = FormatConverter(mapper=prop_map)
        study_converter.add_api_format(study_json["entries"])

        samples_entry = study_converter.get_entry_by_name("samples")

        if samples_entry is not None:
            # The "samples" entry is a NestedListEntry (return list of list)
            if args["entry_format"] == "api":
                return samples_entry.get_api_format()
            elif args["entry_format"] == "form":
                return samples_entry.get_form_format()
        else:
            return []

    @token_required
    @api.expect(sample_model_payload)
    def post(self, study_id, user=None):
        """Add a new sample for a given study"""
        payload = api.payload

        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # 1. Split payload
        entries = payload["entries"]
        entry_format = payload.get("entry_format", "api")
        validate_dict, forms = get_samples_validation_forms(payload)

        if entry_format == "form":
            prop_name_to_syns = get_property_map(key="name", value="synonyms")
        else:
            prop_name_to_syns = None

        # 2. Get study data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # 3. Unify UUIDs with existing entities (including nested ones)
        # Format and clean entity
        sample_converter, _ = get_entity_converter(
            entries,
            entry_format,
            prop_id_to_name,
            prop_name_to_id,
            replace_synonyms=True,
            prop_name_to_syns=prop_name_to_syns,
        )
        new_sample_form_format = sample_converter.get_form_format()

        [new_sample_form_format] = unify_sample_entities_uuids(
            existing_samples=study_converter.get_form_format().get("samples", []),
            new_samples=[new_sample_form_format],
        )

        # 4. Append new samples to "samples" in study
        # Format and clean entity
        sample_converter, _ = get_entity_converter(
            entries=new_sample_form_format,
            entry_format="form",
            prop_id_to_name=None,
            prop_name_to_id=prop_name_to_id,
            replace_synonyms=False,
        )

        # Generate UUID (redundant, UUIDs already generated by unify_sample_entities_uuids)
        sample_converter, sample_uuid = add_uuid_entry_if_missing(
            sample_converter, prop_name_to_id
        )

        study_converter = add_entity_to_study_nested_list(
            study_converter=study_converter,
            entity_converter=sample_converter,
            prop_name_to_id=prop_name_to_id,
            study_list_prop="samples",
        )

        # 5. Validate data against form + unicity
        validate_sample_against_form(
            sample_converter.get_form_format(), validate_dict, forms
        )
        check_samples_unicity(study_converter.get_form_format()["samples"])
        custom_sample_validation(study_converter.get_form_format()["samples"])

        # 6. Update study state, data and upload on DB
        message = "Added sample"
        update_study(study, study_converter, payload, message, user)
        return {"message": message, "uuid": sample_uuid}, 201

    @token_required
    @api.doc(parser=_delete_parser)
    def delete(self, study_id, user=None):
        """Delete all samples from a study given its unique identifier"""
        args = self._delete_parser.parse_args()
        sample_uuids = args["sample_uuids"]

        prop_id_to_name = get_property_map(key="id", value="name")

        # 1. Get study data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # 2. Delete samples
        if sample_uuids is None:
            study_converter.remove_entries(prop_names=["samples"])
        else:
            samples_entry = study_converter.get_entry_by_name("samples")
            for sample_uuid in sample_uuids:
                samples_entry.value.delete_nested_entry("uuid", sample_uuid)

            if len(samples_entry.value.value) == 0:
                study_converter.remove_entries(prop_names=["samples"])

        # 3. Update study state, data and upload on DB
        message = "Deleted samples"
        update_study(study, study_converter, api.payload, message, user)

        return {"message": message}


@api.route("/id/<study_id>/samples/id/<sample_uuid>", strict_slashes=False)
@api.route(
    "/samples/id/<sample_uuid>",
    strict_slashes=False,
    doc={"description": "Alias route for a specific sample without study_id"},
)
@api.param("study_id", "The study identifier")
@api.param("sample_uuid", "The sample identifier")
class ApiStudySampleId(Resource):
    _get_parser = reqparse.RequestParser()
    _get_parser.add_argument("entry_format", **entry_format_param)

    @token_required
    @api.response("200 - api", "Success (API format)", [entry_model_prop_id])
    @api.response("200 - form", "Success (form format)", entry_model_form_format)
    @api.doc(parser=_get_parser)
    def get(self, sample_uuid, study_id=None, user=None):
        """Fetch a specific sample for a given study"""
        args = self._get_parser.parse_args()

        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only sample_uuid
        if study_id is None:
            study_id = find_study_id_from_lvl1_uuid(
                "sample", sample_uuid, prop_name_to_id
            )
            if study_id is None:
                raise Exception(f"Sample not found in any study (uuid = {sample_uuid})")

        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        # The converter is used for its get_entry_by_name() method
        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        samples_entry = study_converter.get_entry_by_name("samples")
        sample_nested_entry = samples_entry.value.find_nested_entry(
            "uuid", sample_uuid
        )[0]

        # The "sample_nested_entry" entry is a NestedEntry (return list of dict)
        if args["entry_format"] == "api":
            return sample_nested_entry.get_api_format()
        elif args["entry_format"] == "form":
            return sample_nested_entry.get_form_format()

    @token_required
    @api.expect(sample_model_payload)
    def put(self, sample_uuid, study_id=None, user=None):
        """Update a sample for a given study"""
        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only sample_uuid
        if study_id is None:
            study_id = find_study_id_from_lvl1_uuid(
                "sample", sample_uuid, prop_name_to_id
            )
            if study_id is None:
                raise Exception(f"Sample not found in any study (uuid = {sample_uuid})")

        payload = api.payload

        # 1. Split payload
        entries = payload["entries"]
        entry_format = payload.get("entry_format", "api")
        validate_dict, forms = get_samples_validation_forms(payload)

        if entry_format == "form":
            prop_name_to_syns = get_property_map(key="name", value="synonyms")
        else:
            prop_name_to_syns = None

        # 2. Get study data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # 3. Get current sample data
        samples_entry = study_converter.get_entry_by_name("samples")
        sample_nested_entry = samples_entry.value.find_nested_entry(
            "uuid", sample_uuid
        )[0]
        sample_converter = FormatConverter(mapper=prop_id_to_name)
        sample_converter.entries = sample_nested_entry.value

        # 4. Unify UUIDs with existing entities (including nested ones)
        # Format and clean entity
        new_sample_converter, _ = get_entity_converter(
            entries,
            entry_format,
            prop_id_to_name,
            prop_name_to_id,
            replace_synonyms=True,
            prop_name_to_syns=prop_name_to_syns,
        )

        new_sample_form_format = new_sample_converter.get_form_format()

        [new_sample_form_format] = unify_sample_entities_uuids(
            existing_samples=study_converter.get_form_format().get("samples", []),
            new_samples=[new_sample_form_format],
        )

        # 5. Clean new data and get entries to remove
        # Format and clean entity
        new_sample_converter, entries_to_remove = get_entity_converter(
            entries=new_sample_form_format,
            entry_format="form",
            prop_id_to_name=None,
            prop_name_to_id=prop_name_to_id,
            replace_synonyms=False,
        )

        # 6. Update current sample by adding, updating and deleting entries
        # Nested entries not present in the original form are ignored
        # won't be deleted if not present in the new data), it needs to be None or "" to be deleted
        sample_converter.add_or_update_entries(new_sample_converter.entries)
        sample_converter.remove_entries(entries=entries_to_remove)
        sample_nested_entry.value = sample_converter.entries

        # 7. Validate data against form + unicity
        validate_sample_against_form(
            sample_converter.get_form_format(), validate_dict, forms
        )
        check_samples_unicity(study_converter.get_form_format()["samples"])
        custom_sample_validation(study_converter.get_form_format()["samples"])

        # 8. Update study state, data and upload on DB
        message = "Updated sample"
        update_study(study, study_converter, payload, message, user)
        return {"message": message}

    @token_required
    def delete(self, sample_uuid, study_id=None, user=None):
        """Delete a sample from a study given its unique identifier"""
        prop_id_to_name = get_property_map(key="id", value="name")
        prop_name_to_id = reverse_map(prop_id_to_name)

        # Used for helper route using only sample_uuid
        if study_id is None:
            study_id = find_study_id_from_lvl1_uuid(
                "sample", sample_uuid, prop_name_to_id
            )
            if study_id is None:
                raise Exception(f"Sample not found in any study (uuid = {sample_uuid})")

        # 1. Get study data
        study = Study.objects().get(id=study_id)
        study_json = marshal(study, study_model)

        study_converter = FormatConverter(mapper=prop_id_to_name)
        study_converter.add_api_format(study_json["entries"])

        # 2. Delete specific entity
        samples_entry = study_converter.get_entry_by_name("samples")
        samples_entry.value.delete_nested_entry("uuid", sample_uuid)

        if len(samples_entry.value.value) == 0:
            study_converter.remove_entries(prop_names=["samples"])

        # 3. Update study state, data and upload on DB
        message = f"Deleted sample"
        update_study(study, study_converter, api.payload, message, user)

        return {"message": message}


def get_samples_validation_forms(payload):
    """
    Args:
        payload (dict): API Payload with "validate" and "form_names"

    Returns:
        [dict]: validate_dict (which entities should be validated)
        [dict]: forms used for validation
    """
    validate_dict = payload.get("validate", None)
    form_names = payload.get("form_names", None)

    forms = {}
    for entity_name, validate in validate_dict.items():
        if validate:
            if not entity_name in form_names.keys():
                raise Exception(
                    f"The validation of '{entity_name}' is set to True but the"
                    " corresponding form name is missing from 'form_names'."
                )
            forms[entity_name] = app.form_manager.get_form_by_name(
                form_name=form_names[entity_name]
            )

    return validate_dict, forms


def check_samples_unicity(samples_form_format):
    """
    Check if unicity constraints of certain properties are met
    These can be define in ENV variables: UNIQUE_SAMPLE_PROPS, ...
    Format: "a,b;c,d" = the combinations a,b and c,d must me unique for each entity
    """

    if not app.config["UNIQUE_SAMPLE_PROPS"]:
        return

    props_groups_to_check = app.config["UNIQUE_SAMPLE_PROPS"].split(";")

    for props_group in props_groups_to_check:
        props = props_group.split(",")
        unique_values = []

        for sample in samples_form_format:
            value = [sample.get(p) for p in props]
            if None in value:
                continue

            if value in unique_values:
                raise Exception(
                    f"Samples must have unique combination of {props} (sample {sample['sample_id']} failed)"
                )
            else:
                unique_values.append(value)


def custom_sample_validation(samples_form_format):
    """
    Custom validation of samples
    Example: no ";" allowing in "sample_id"
    """

    for sample in samples_form_format:
        if ";" in sample["sample_id"]:
            raise Exception(
                f"The character ';' is not allowed in the property 'sample_id'"
            )

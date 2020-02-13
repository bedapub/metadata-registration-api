from flask_restx import Namespace, Resource, fields
from flask_restx import reqparse, inputs, marshal

from database_model.model import Form, DataObjects
from .api_props import property_model_id
from .decorators import token_required

api = Namespace("Forms", description="Form related operations")


# Custom fields
# ----------------------------------------------------------------------------------------------------------------------

class ArgsField(fields.Raw):
    """ Custom field for args field. If the value contains a DataObject, it is modeled with the objects model """

    def format(self, value):
        if isinstance(value, DataObjects):
            return marshal(value, objects_model)

        return value


class SubformAddField(fields.Raw):
    """ Custom field for subforms """

    def format(self, value):
        return marshal(value, field_add_model)


class SubformField(fields.Raw):
    """ Custom field for subforms """

    def format(self, value):
        return marshal(value, field_model)


# Model definitions
# ----------------------------------------------------------------------------------------------------------------------


object_model = api.model("Object", {
    "class_name": fields.String(description="The class in which the object is represented"),
    "property": fields.Nested(property_model_id),
    "args": ArgsField(),
    "kwargs": fields.Raw(),

    "fields": fields.List(SubformField)
})

objects_model = api.model("Objects", {
    "objects": fields.List(fields.Nested(object_model))
})

field_add_model = api.model("Add Field", {
    "label": fields.String(description="Human readable name of the field. If set, it will overwrite the label of the "
                                       "property"),
    "property": fields.String("Unique identifier of a property"),
    "class_name": fields.String(description="The class by which the field is represented"),
    "description": fields.String(description="Detailed description of the purpose of the field"),
    "args": fields.Raw(),
    "kwargs": fields.Raw(),

    "name": fields.String(),
    "fields": fields.List(SubformAddField),
})

form_add_model = api.model("Add Form", {
    "label": fields.String(description="Human readable name of the entry"),
    "name": fields.String(description="Internal representation of the entry (in snake_case)"),
    "fields": fields.List(fields.Nested(field_add_model)),
    "description": fields.String(description="Detailed description of the intended use", default=""),
    "deprecated": fields.Boolean(description="Indicator, if the entry is no longer used.", default=False)
})

field_model = api.model("Field", {
    "label": fields.String(description="Human readable name of the field. If set, it will overwrite the label of the "
                                       "property"),
    "property": fields.Nested(property_model_id),
    # TODO: Why is class_name optional?
    "class_name": fields.String(description="The class by which the field is represented", optional=True),
    "description": fields.String(description="Detailed description of the purpose of the field"),
    "args": ArgsField(),
    "kwargs": fields.Raw(),

    "name": fields.String(),
    "fields": fields.List(SubformField)
})

form_model = api.model("Forms", {
    "label": fields.String(description="Human readable name of the entry"),
    "name": fields.String(description="Internal representation of the entry (in snake_case)"),
    "description": fields.String(description="Detailed description of the intended use", default=""),
    "fields": fields.List(fields.Nested(field_model)),
    "deprecated": fields.Boolean(description="Indicator, if the entry is no longer used.", default=False)
})

form_model_id = api.inherit("Form with id", form_model, {
    "id": fields.String(attribute="pk", description="Unique identifier of the entry"),
})


@api.route("/")
class ApiForm(Resource):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument("deprecated",
                            type=inputs.boolean,
                            location="args",
                            default=False,
                            help="Boolean indicator which determines if deprecated entries should be returned as well",
                            )

    _delete_parser = reqparse.RequestParser()
    _delete_parser.add_argument("complete",
                               type=inputs.boolean,
                               default=False,
                               help="Boolean indicator to remove an entry instead of deprecating it (cannot be undone)"
                               )

    @api.marshal_list_with(form_model_id)
    @api.expect(parser=get_parser)
    def get(self):
        """ Fetch a list with all entries """
        # Convert query parameters
        args = self.get_parser.parse_args()
        include_deprecate = args["deprecated"]

        if not include_deprecate:
            res = Form.objects(deprecated=False).all()
        else:
            # Include entries which are deprecated
            res = Form.objects().all()
        return list(res)

    @token_required
    @api.expect(form_add_model)
    def post(self, user):
        """ Add a new entry """
        entry = Form(**api.payload)
        entry.save()
        return {"message": f"Add entry '{entry.name}'",
                "id": str(entry.id)}, 201

    @token_required
    @api.expect(parser=_delete_parser)
    def delete(self, user):
        """ Delete all entries """
        args = self._delete_parser.parse_args()
        force_delete = args["complete"]

        entry = Form.objects().all()
        if not force_delete:
            entry.update(deprecated=True)
            return {"message": f"Deprecate all entries"}
        else:
            entry.delete()
            return {"message": f"Delete all entries"}


@api.route("/id/<id>")
@api.route("/id/<id>/")
@api.param("id", "The property identifier")
class ApiForm(Resource):
    _delete_parser = reqparse.RequestParser()
    _delete_parser.add_argument("complete",
                               type=inputs.boolean,
                               default=False,
                               help="Boolean indicator to remove an entry instead of deprecating it (cannot be undone)"
                               )

    @api.marshal_with(form_model_id)
    def get(self, id):
        """Fetch an entry given its unique identifier"""
        res = Form.objects(id=id).get()
        return res

    @token_required
    @api.expect(form_model)
    def put(self, user, id):
        """ Update an entry given its unique identifier """
        entry = Form.objects(id=id).get()
        entry.update(**api.payload)
        return {"message": f"Update entry '{entry.name}'"}

    @token_required
    @api.expect(parser=_delete_parser)
    def delete(self, user, id):
        """ Delete an entry given its unique identifier """
        args = self._delete_parser.parse_args()
        force_delete = args["complete"]

        entry = Form.objects(id=id).get()
        if not force_delete:
            entry.update(deprecated=True)
            return {"message": f"Deprecate entry '{entry.name}'"}
        else:
            entry.delete()
            return {"message": f"Delete entry {entry.name}"}

from bson import ObjectId

from flask_restplus import Namespace, Resource, fields
from flask_restplus import reqparse, inputs, marshal

from api_service.model import Form, DataObjects
from api_service.api.api_props import property_model_id
from api_service.api.decorators import token_required


api = Namespace("Form", description="Form related operations")


class ArgsField(fields.Raw):
    """ A special field which marshals itself dependent on the given value type """

    def format(self, value):
        if isinstance(value, DataObjects):
            return marshal(value, objects_model)

        return value


object_model = api.model("Object", {
    "class_name": fields.String(),
    "property": fields.Nested(property_model_id),
    "args": ArgsField(),
    "kwargs": fields.String()
})

objects_model = api.model("Objects", {
    "objects": fields.List(fields.Nested(object_model))
})

object_model = api.model("Object", {
    "class_name": fields.String(),
    "property": fields.Nested(property_model_id),
    "args": fields.String(),
    "kwargs": fields.String()
})

mapping = {
    'objects': fields.Nested(object_model)
}

field_add_model = api.model("Add Field", {
    "label": fields.String(),
    "property": fields.String(),
    "class_name": fields.String(),
    "description": fields.String(),
    "args": fields.Raw(),
    "kwargs": fields.Raw(),
})

form_add_model = api.model("Add Form", {
    "label": fields.String(description="Human readable name of the entry"),
    "name": fields.String(description="Internal representation of the entry (in snake_case)"),
    "fields": fields.List(fields.Nested(field_add_model)),
    "description": fields.String(description="Detailed description of the intended use", default=""),
    "deprecated": fields.Boolean(description="Indicator, if the entry is no longer used.", default=False)
})


field_model = api.model("Field", {
    "label": fields.String(),
    "property": fields.Nested(property_model_id),
    "class_name": fields.String(optional=True),
    "description": fields.String(),
    "args": ArgsField(),
    "kwargs": fields.Raw(),
})


form_model = api.model("Form", {
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
    get_parser.add_argument('deprecated',
                            type=inputs.boolean,
                            location="args",
                            default=False,
                            help="Boolean indicator which determines if deprecated entries should be returned as well",
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
        p = Form(**api.payload)
        p.save()
        return {"message": "Add entry '{}'".format(p.name)}, 201


@api.route("/id/<id>")
@api.param("id", "The property identifier")
class ApiForm(Resource):

    delete_parser = reqparse.RequestParser()
    delete_parser.add_argument('complete',
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
        return {"message": "Update entry '{}'".format(entry.name)}

    @token_required
    @api.expect(parser=delete_parser)
    def delete(self, user, id):
        """ Delete an entry given its unique identifier """
        args = self.delete_parser.parse_args()
        force_delete = args["complete"]

        entry = Form.objects(id=id).get()
        if not force_delete:
            entry.update(deprecated=True)
            return {"message": "Deprecate entry '{}'".format(entry.name)}
        else:
            entry.delete()
            return {"message": "Delete entry {}".format(entry.name)}

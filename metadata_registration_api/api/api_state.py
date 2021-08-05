from flask_restx import Namespace, Resource, fields
from flask import current_app as app

from metadata_registration_api.mongo_utils import get_states
from bson.objectid import ObjectId

api = Namespace("States", description="State related operations")


# Model definition
# ----------------------------------------------------------------------------------------------------------------------

strategy_model = api.model(
    "Strategy",
    {
        "name": fields.String(),
        "value": fields.String(),
        "state_if_true": fields.String(),
    },
)

state_model = api.model(
    "State",
    {
        "_id": fields.String(),
        "name": fields.String(),
        "strategies_create_study": fields.List(fields.Nested(strategy_model)),
        "strategies_change_state": fields.List(fields.Nested(strategy_model)),
        "ui_actions": fields.Raw(),
    },
)

# Routes
# ----------------------------------------------------------------------------------------------------------------------


@api.route("")
class ApiState(Resource):
    @api.marshal_with(state_model)
    @api.response("200", "Success")
    def get(self):
        """ Fetch a list with all entries """
        states = get_states(app)
        return list(states)


@api.route("/id/<id>", strict_slashes=False)
@api.param("id", "The state id")
class ApiStateId(Resource):
    @api.marshal_with(state_model)
    @api.response("200", "Success")
    def get(self, id):
        """ Fetch a specific entries """
        state = get_states(app, q={"_id": ObjectId(id)})[0]
        return state


@api.route("/name/<name>", strict_slashes=False)
@api.param("name", "The state name")
class ApiStateName(Resource):
    @api.marshal_with(state_model)
    @api.response("200", "Success")
    def get(self, name):
        """ Fetch a specific entries """
        state = get_states(app, q={"name": name})[0]
        return state
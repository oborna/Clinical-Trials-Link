from google.cloud import datastore
from flask import Blueprint, request, make_response
import json
import constants

client = datastore.Client(project="clinical-trials-link")

bp = Blueprint("users", __name__, url_prefix="/users")

@bp.route("", methods=["GET"])
def get_users():

    if request.method == "GET":

        # Check media type requested by client
        if "application/json" not in request.accept_mimetypes:
            error_message = {"Error": "Unsupported media type requested by client."}
            return (error_message, 406)
            
        user_query = client.query(kind=constants.users)
        user_results = list(user_query.fetch())

        for user in user_results:
            user["id"] = user.key.id
            user["self"] = request.url + "/" + str(user.key.id)

        returned_users = make_response(json.dumps(user_results, indent=4))
        returned_users.headers.set("Content-Type", "application/json")
        return (returned_users, 200)

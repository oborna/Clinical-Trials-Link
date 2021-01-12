from google.cloud import datastore
from flask import Blueprint, request, make_response
import json
import constants
import request_validation

client = datastore.Client(project="clinical-trials-link")

bp = Blueprint("condition", __name__, url_prefix="/conditions")

client_id = r"394192668733-f86tkpt35f403k7oiidoabdaldc1dp9r.apps.googleusercontent.com"
client_secret = r"0wQqw5I830h5gdObbbt1tizf"

# View All Conditions
@bp.route("", methods=["GET"])
def get_conditions():

    if request.method == "GET":

        # Check media type requested by client
        if "application/json" not in request.accept_mimetypes:
            error_message = {"Error": "Unsupported media type requested by client."}
            return (error_message, 406)

        query = client.query(kind=constants.conditions)
        results = list(query.fetch())   #TODO: Filter out all private trials?

        for condition in results:
            condition["id"] = condition.key.id
            condition["self"] = request.url + "/" + str(condition.key.id)

        returned_conditions = make_response(json.dumps(results, indent=4))
        returned_conditions.headers.set("Content-Type", "application/json")

        return (returned_conditions, 200)

    else:
        return ("Method not recognized", 400)        

# Create a Condition
@bp.route("", methods=["POST"])
def post_condition():

    if request.method == "POST":

        # Check media type requested by client
        if "application/json" not in request.accept_mimetypes:
            #error_message = {"Error": "Unsupported media type in 'Accept' request header."}
            error_message = {"Error": "Unsupported media type requested by client."}
            return (error_message, 406)

        # Check media type sent by client
        if "application/json" not in request.content_type:
            #error_message = {"Error": "Unsupported media type in 'Content-Type' request header."}
            error_message = {"Error": "Unsupported media type sent by client."}
            return (error_message, 415)

        content = request.get_json()
        attributes = content.keys()

        # Check request body attributes
        possible_attributes = ["name", "description", "types"]
        required_attributes = ["name"]
        if request_validation.has_valid_attributes(attributes, possible_attributes, required_attributes) is False:
            error_message = {"Error": "A required attribute is missing and/or an extraneous or invalid attribute was provided."}
            return (error_message, 400)

        # Check "name" uniqueness constraint
        if request_validation.is_unique("name", content["name"], constants.conditions) is False:
            error_message = {"Error": "A condition with this name already exists."}
            return (error_message, 409)

        # Create and save condition to datastore
        new_condition = datastore.entity.Entity(key=client.key(constants.conditions))
        new_condition.update({"name": content["name"], "description": "",
        "types": [], "clinical_trials": []})

        if "description" in attributes:
            new_condition.update({"description": content["description"]})

        if "types" in attributes:
            new_condition.update({"types": content["types"]})

        client.put(new_condition)
        
        # Return new condition
        new_condition["id"] = new_condition.key.id
        new_condition["self"] = request.url + "/" + str(new_condition.key.id)
        returned_condition = make_response(json.dumps(new_condition, indent=4))
        returned_condition.headers.set("Content-Type", "application/json")
        return (returned_condition, 201)

    else:
        return ("Method not recognized", 400)

# View a Condition
@bp.route("/<condition_id>", methods=["GET"])
def get_condition(condition_id):

    if request.method == "GET":

        # Check media type requested by client
        if "application/json" not in request.accept_mimetypes:
            error_message = {"Error": "Unsupported media type requested by client."}
            return (error_message, 406)

        condition_key = client.key(constants.conditions, int(condition_id))
        condition = client.get(key=condition_key)

        if condition is None:
            error_message = {"Error": "No condition with this ID exists."}
            return (error_message, 404)

        else:
            condition["id"] = condition.key.id  #TODO: Filter out all private trials?
            condition["self"] = request.url

            returned_condition = make_response(json.dumps(condition, indent=4))
            returned_condition.headers.set("Content-Type", "application/json")
            return (returned_condition, 200)
   
    else:
        return ("Method not recognized", 400) 

# Edit a Condition (patch)
@bp.route("/<condition_id>", methods=["PATCH"])
def patch_condition(condition_id):
    
    if request.method == "PATCH":

        # Check media type requested by client
        if "application/json" not in request.accept_mimetypes:
            error_message = {"Error": "Unsupported media type requested by client."}
            return (error_message, 406)

        # Check media type sent by client
        if "application/json" not in request.content_type:
            error_message = {"Error": "Unsupported media type sent by client."}
            return (error_message, 415)

        condition_key = client.key(constants.conditions, int(condition_id))
        condition = client.get(key=condition_key)

        if condition is None:
            error_message = {"Error": "No condition with this ID exists."}
            return (error_message, 404)
        
        content = request.get_json()
        attributes = content.keys()

        # Check request body attributes
        possible_attributes = ["name", "description", "types"]
        if not attributes or request_validation.has_valid_attributes(attributes, possible_attributes) is False:
            error_message = {"Error": "A required attribute is missing and/or an extraneous or invalid attribute was provided."}
            return (error_message, 400)

        # Check "name" uniqueness constraint
        if "name" in attributes:
            if request_validation.is_unique("name", content["name"], constants.conditions) is False:
                error_message = {"Error": "A condition with this name already exists."}
                return (error_message, 409)

        if "name" in attributes:
            updated_name = content["name"]
            condition.update({"name": updated_name})
        if "description" in attributes:
            updated_description = content["description"]
            condition.update({"description": updated_description})
        if "types" in attributes:
            updated_types = content["types"]
            condition.update({"types": updated_types})               
        
        client.put(condition)

        condition["id"] = condition.key.id
        condition["self"] = request.url
        returned_condition = make_response(json.dumps(condition, indent=4))
        returned_condition.headers.set("Content-Type", "application/json") 
        return (returned_condition, 200)
    
    else:
        return ("Method not recognized", 400)

# Edit a Condition (put)
@bp.route("/<condition_id>", methods=["PUT"])
def put_condition(condition_id):
    
    if request.method == "PUT":

        # Check media type requested by client
        if "application/json" not in request.accept_mimetypes:
            error_message = {"Error": "Unsupported media type requested by client."}
            return (error_message, 406)

        # Check media type sent by client
        if "application/json" not in request.content_type:
            error_message = {"Error": "Unsupported media type sent by client."}
            return (error_message, 415)

        condition_key = client.key(constants.conditions, int(condition_id))
        condition = client.get(key=condition_key)

        if condition is None:
            error_message = {"Error": "No condition with this ID exists."}
            return (error_message, 404)
        
        content = request.get_json()
        attributes = content.keys()

        # Check request body attributes
        possible_attributes = ["name", "description", "types"]
        if request_validation.has_valid_attributes(attributes, possible_attributes) is False:
            error_message = {"Error": "A required attribute is missing and/or an extraneous or invalid attribute was provided."}
            return (error_message, 400)

        # Check "name" uniqueness constraint
        if "name" in attributes:
            if request_validation.is_unique("name", content["name"], constants.conditions) is False:
                error_message = {"Error": "A condition with this name already exists."}
                return (error_message, 409)

        condition.update({"name": content["name"]})

        if "description" in attributes:
            updated_description = content["description"]
            condition.update({"description": updated_description})
        if "types" in attributes:
            updated_types = content["types"]
            condition.update({"types": updated_types}) 
            
        client.put(condition)

        condition["id"] = condition.key.id
        condition["self"] = request.url
        returned_condition = make_response(json.dumps(condition, indent=4))
        returned_condition.headers.set("Content-Type", "application/json") 
        return (returned_condition, 200)
    
    else:
        return ("Method not recognized", 400)

# Delete a Condition
@bp.route("/<condition_id>", methods=["DELETE"])
def delete_condition(condition_id):
    
    if request.method == "DELETE":
        condition_key = client.key(constants.conditions, int(condition_id))
        condition = client.get(key=condition_key)

        if condition is None:
            error_message = {"Error": "No condition with this ID exists."}
            return (error_message, 404)
        
        if condition["clinical_trials"]:
            error_message = {"Error": "Clinical trials are currently associated with this condition. Please disassociate these clinical trials from this condition before attempting to delete this condition."}
            return (error_message, 409)           

        client.delete(condition_key)
        return ("", 204)
    
    else:
        return ("Method not recognized", 400)

# Method Not Allowed
@bp.route("/<condition_id>", methods=["POST"])
def post_condition_not_allowed(condition_id):
    
    if request.method == "POST":

        error_message = {"Error": "Cannot POST to this endpoint."}
        return (error_message, 405)
    
    else:
        return ("Method not recognized", 400)

# NOTE: The below endpoint is not required per the project specifications. I did not finish implementing it due to time constraints.
"""
# View All The Clinical Trials Associated With A Condition
@bp.route("/<condition_id>/trials", methods=["GET"])
def get_condition_trials(condition_id):
    
    if request.method == "GET":

        # Check media type requested by client
        if "application/json" not in request.accept_mimetypes:
            error_message = {"Error": "Unsupported media type requested by client."}
            return (error_message, 406)
            
        condition_key = client.key(constants.conditions, int(condition_id))
        condition = client.get(key=condition_key)

        if condition is None:
            error_message = {"Error": "No condition with this ID exists."}
            return (error_message, 404)
        
        else:
            trials = []
            for trial_id in condition["clinical_trials"]: # TODO: What if there are none?
                trial_key = client.key(constants.clinicaltrials, int(trial_id))
                trial = client.get(key=trial_key)
                trial["id"] = trial.key.id
                trial["self"] = request.url + "/" + str(trial.key.id) # TODO: Fix URL
                trials.append(trial)
            
            print(trials)
            print(type(trials))

            returned_trials = make_response(json.dumps(trials, indent=4))
            returned_trials.headers.set("Content-Type", "application/json")
            print(returned_trials)
            
            return (returned_trials, 200)
    
    else:
        return ("Method not recognized", 400)
"""
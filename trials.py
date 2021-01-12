from google.cloud import datastore
from flask import Blueprint, request, make_response
import json
import constants
import request_validation

# Google Authorization
from google.oauth2 import id_token
from google.auth.transport import requests

client = datastore.Client(project="clinical-trials-link")

bp = Blueprint("trials", __name__, url_prefix="/trials")

client_id = r"394192668733-f86tkpt35f403k7oiidoabdaldc1dp9r.apps.googleusercontent.com"
client_secret = r"0wQqw5I830h5gdObbbt1tizf"

# View All Clinical Trials
@bp.route("", methods=["GET"])
def get_trials():

    if request.method == "GET":

        # Check media type requested by client
        if "application/json" not in request.accept_mimetypes:
            error_message = {"Error": "Unsupported media type requested by client."}
            return (error_message, 406)

        # If no authorization header is present, return error
        if "authorization" not in request.headers:
            error_message = {"Error": "The request is missing an authorization header."}
            return (error_message, 401)

        # Get and check the authorization header's value
        authorization_header = request.headers.get("authorization")  
        if request_validation.has_valid_auth_header(authorization_header) is False:
            error_message = {"Error": "The request's authorization header value is invalid."}
            return (error_message, 401)  

        # Get and check the validity of the JSON Web Token
        json_web_token = authorization_header[7:]   
        validation_request = requests.Request()
        try:
            jwt_info = id_token.verify_oauth2_token(json_web_token, validation_request, client_id)
        except ValueError:
            error_message = {"Error": "The JWT provided in the request's authorization header is invalid."}
            return (error_message, 401)
        except:
            error_message = {"Error": "The JWT provided in the request's authorization header is invalid."}
            return (error_message, 401)   

        # Check If JWT Is Associated With An Existing User Using Email In JWT
        email = jwt_info["email"]
        user_exists, user_id, user_email = request_validation.email_associated_with_user(email)

        if user_exists is False:
            error_message = {"Error": "The JWT provided in the request's authorization header is not associated with an existing user."}
            return (error_message, 403)

        query = client.query(kind=constants.trials)
        results = list(query.fetch())

        final_results = []
        for trial in results:
            if trial["public"] is True or trial["created_by"]["id"] == user_id:
                trial["id"] = trial.key.id
                trial["self"] = request.url + "/" + str(trial.key.id)
                trial["created_by"].update({"self": request.url[:-23] + "users/" + str(user_id)})

                if trial["condition"]:
                    trial["condition"].update({"self": request.url[:-23] + "conditions/" + str(trial["condition"]["id"])})

                final_results.append(trial)

        returned_trials = make_response(json.dumps(final_results, indent=4))
        returned_trials.headers.set("Content-Type", "application/json")
        
        return (returned_trials, 200)

    else:
        return ("Method not recognized", 400)        

# Create a Clinical Trial
@bp.route("", methods=["POST"])
def post_trial():

    if request.method == "POST":

        # Check media type requested by client
        if "application/json" not in request.accept_mimetypes:
            error_message = {"Error": "Unsupported media type requested by client."}
            return (error_message, 406)

        # Check media type sent by client
        if "application/json" not in request.content_type:
            error_message = {"Error": "Unsupported media type sent by client."}
            return (error_message, 415)

        # If no authorization header is present, return error
        if "authorization" not in request.headers:
            error_message = {"Error": "The request is missing an authorization header."}
            return (error_message, 401)

        # Get and check the authorization header's value
        authorization_header = request.headers.get("authorization")  
        if request_validation.has_valid_auth_header(authorization_header) is False:
            error_message = {"Error": "The request's authorization header value is invalid."}
            return (error_message, 401)  

        # Get and check the validity of the JSON Web Token
        json_web_token = authorization_header[7:]   
        validation_request = requests.Request()
        try:
            jwt_info = id_token.verify_oauth2_token(json_web_token, validation_request, client_id)
        except ValueError:
            error_message = {"Error": "The JWT provided in the request's authorization header is invalid."}
            return (error_message, 401)
        except:
            error_message = {"Error": "The JWT provided in the request's authorization header is invalid."}
            return (error_message, 401)   

        # Check If JWT Is Associated With An Existing User Using Email In JWT
        email = jwt_info["email"]
        user_exists, user_id, user_email = request_validation.email_associated_with_user(email)

        if user_exists is False:
            error_message = {"Error": "The JWT provided in the request's authorization header is not associated with an existing user."}
            return (error_message, 403)   

        content = request.get_json()
        attributes = content.keys()

        # Check request body attributes
        possible_attributes = ["public", "name", "phase", "status", "condition", "study_type", "intervention_type", "intervention_name", "companies", "summary", "website"]
        required_attributes = ["public", "name", "phase", "status", "study_type", "intervention_type", "intervention_name", "companies"]
        if not attributes or request_validation.has_valid_attributes(attributes, possible_attributes, required_attributes) is False:
            error_message = {"Error": "A required attribute is missing and/or an extraneous or invalid attribute was provided."}
            return (error_message, 400)

        # Check "name" uniqueness constraint
        if request_validation.is_unique("name", content["name"], constants.trials) is False:
            error_message = {"Error": "A clinical trial with this name already exists."}
            return (error_message, 409)

        # Check if "condition" exists
        if "condition" in attributes:
            condition = content["condition"]
            condition_exists, condition_id, condition_name = request_validation.condition_exists(condition)
            if condition_exists is False:       
                error_message = {"Error": "The provided condition does not exist in the API database."}
                return (error_message, 404)

        # Create and save clinical trial to datastore
        new_trial = datastore.entity.Entity(key=client.key(constants.trials))
        new_trial.update({"created_by": {"id": user_id}, "public": content["public"], "name": content["name"],
        "phase": content["phase"], "status": content["status"], "condition": {}, 
        "study_type": content["study_type"], "intervention_type": content["intervention_type"],
        "intervention_name": content["intervention_name"], "companies": content["companies"],
        "summary": "", "website": ""})
        
        if "condition" in attributes:
            new_trial.update({"condition": {"id": condition_id}})
            # Add Clinical Trial To Its Associated Condition
            condition_key = client.key(constants.conditions, int(condition_id))
            condition = client.get(key=condition_key)
            condition["clinical_trials"].append({"id": new_trial.key.id})
            client.put(condition)          

        if "summary" in attributes:
            new_trial.update({"summary": content["summary"]})

        if "website" in attributes:
            new_trial.update({"website": content["website"]})

        client.put(new_trial)
        
            # Add Clinical Trial To Its Associated Condition
        if "condition" in attributes:
            condition_key = client.key(constants.conditions, int(condition_id))
            condition = client.get(key=condition_key)
            condition["clinical_trials"].append({"id": new_trial.key.id})
            client.put(condition)   

        # Return new clinical trial
        new_trial["id"] = new_trial.key.id
        new_trial["self"] = request.url + "/" + str(new_trial.key.id)
        new_trial["created_by"].update({"self": request.url[:-6] + "users/" + str(user_id)})

        if "condition" in attributes:
            new_trial["condition"].update({"self": request.url[:-6] + "conditions/" + str(condition_id)})

        returned_trial = make_response(json.dumps(new_trial, indent=4))
        returned_trial.headers.set("Content-Type", "application/json")
        return (returned_trial, 201)

    else:
        return ("Method not recognized", 400)

# View a Clinical Trial
@bp.route("/<trial_id>", methods=["GET"])
def get_trial(trial_id):

    if request.method == "GET":

        # Check media type requested by client
        if "application/json" not in request.accept_mimetypes:
            error_message = {"Error": "Unsupported media type requested by client."}
            return (error_message, 406)

        # If no authorization header is present, return error
        if "authorization" not in request.headers:
            error_message = {"Error": "The request is missing an authorization header."}
            return (error_message, 401)

        # Get and check the authorization header's value
        authorization_header = request.headers.get("authorization")  
        if request_validation.has_valid_auth_header(authorization_header) is False:
            error_message = {"Error": "The request's authorization header value is invalid."}
            return (error_message, 401)  

        # Get and check the validity of the JSON Web Token
        json_web_token = authorization_header[7:]   
        validation_request = requests.Request()
        try:
            jwt_info = id_token.verify_oauth2_token(json_web_token, validation_request, client_id)
        except ValueError:
            error_message = {"Error": "The JWT provided in the request's authorization header is invalid."}
            return (error_message, 401)
        except:
            error_message = {"Error": "The JWT provided in the request's authorization header is invalid."}
            return (error_message, 401)   

        # Check If JWT Is Associated With An Existing User Using Email In JWT
        email = jwt_info["email"]
        user_exists, user_id, user_email = request_validation.email_associated_with_user(email)

        if user_exists is False:
            error_message = {"Error": "The JWT provided in the request's authorization header is not associated with an existing user."}
            return (error_message, 403)

        trial_key = client.key(constants.trials, int(trial_id))
        trial = client.get(key=trial_key)

        if trial is None:
            error_message = {"Error": "No clinical trial with this ID exists."}
            return (error_message, 404)

        if trial["public"] is True or trial["created_by"]["id"] == user_id:

            trial["id"] = trial.key.id
            trial["self"] = request.url
            trial["created_by"].update({"self": request.url[:-23] + "users/" + str(user_id)})

            if trial["condition"]:
                trial["condition"].update({"self": request.url[:-23] + "conditions/" + str(trial["condition"]["id"])})

            returned_trial = make_response(json.dumps(trial, indent=4))
            returned_trial.headers.set("Content-Type", "application/json")
            return (returned_trial, 200)

        else:
            error_message = {"error": "The requested clinical trial is not public and belongs to another user."}
            return (error_message, 403)
   
    else:
        return ("Method not recognized", 400)

# Edit a Clinical Trial (patch)
@bp.route("/<trial_id>", methods=["PATCH"])
def patch_trial(trial_id):
    
    if request.method == "PATCH":

        # Check media type requested by client
        if "application/json" not in request.accept_mimetypes:
            error_message = {"Error": "Unsupported media type requested by client."}
            return (error_message, 406)

        # Check media type sent by client
        if "application/json" not in request.content_type:
            error_message = {"Error": "Unsupported media type sent by client."}
            return (error_message, 415)

        # If no authorization header is present, return error
        if "authorization" not in request.headers:
            error_message = {"Error": "The request is missing an authorization header."}
            return (error_message, 401)

        # Get and check the authorization header's value
        authorization_header = request.headers.get("authorization")  
        if request_validation.has_valid_auth_header(authorization_header) is False:
            error_message = {"Error": "The request's authorization header value is invalid."}
            return (error_message, 401)  

        # Get and check the validity of the JSON Web Token
        json_web_token = authorization_header[7:]   
        validation_request = requests.Request()
        try:
            jwt_info = id_token.verify_oauth2_token(json_web_token, validation_request, client_id)
        except ValueError:
            error_message = {"Error": "The JWT provided in the request's authorization header is invalid."}
            return (error_message, 401)
        except:
            error_message = {"Error": "The JWT provided in the request's authorization header is invalid."}
            return (error_message, 401)   

        # Check If JWT Is Associated With An Existing User Using Email In JWT
        email = jwt_info["email"]
        user_exists, user_id, user_email = request_validation.email_associated_with_user(email)

        if user_exists is False:
            error_message = {"Error": "The JWT provided in the request's authorization header is not associated with an existing user."}
            return (error_message, 403)  

        trial_key = client.key(constants.trials, int(trial_id))
        trial = client.get(key=trial_key)

        if trial is None:
            error_message = {"Error": "No clinical trial with this ID exists."}
            return (error_message, 404)

        if trial["created_by"]["id"] != user_id:
            error_message = {"Error": "This trial belongs to another user and cannot be edited."}
            return (error_message, 403)

        content = request.get_json()
        attributes = content.keys()

        # Check request body attributes
        possible_attributes = ["public", "name", "phase", "status", "condition", "study_type", "intervention_type", "intervention_name", "companies", "summary", "website"]
        if not attributes or request_validation.has_valid_attributes(attributes, possible_attributes) is False:
            error_message = {"Error": "A required attribute is missing and/or an extraneous or invalid attribute was provided."}
            return (error_message, 400)

        # Check "name" uniqueness constraint
        if "name" in attributes:
            if request_validation.is_unique("name", content["name"], constants.trials) is False:
                error_message = {"Error": "A clinical trial with this name already exists."}
                return (error_message, 409)

        # Check if "condition" was erroneously provided
        if "condition" in attributes:
                error_message = {"Error": "Cannot alter the condition associated with a clinical trial using this endpoint."}
                return (error_message, 403)    

        for attribute in attributes:
            trial.update({attribute: content[attribute]}) # TODO: Do this everywhere

        client.put(trial)

        trial["id"] = trial.key.id
        trial["self"] = request.url
        trial["created_by"].update({"self": request.url[:-23] + "users/" + str(user_id)})

        if trial["condition"]:
            trial["condition"].update({"self": request.url[:-23] + "conditions/" + str(trial["condition"]["id"])})

        returned_trial = make_response(json.dumps(trial, indent=4))
        returned_trial.headers.set("Content-Type", "application/json") 
        return (returned_trial, 200)
    
    else:
        return ("Method not recognized", 400)

# Edit a Clinical Trial (put)
@bp.route("/<trial_id>", methods=["PUT"])
def put_trial(trial_id):
    
    if request.method == "PUT":

        # Check media type requested by client
        if "application/json" not in request.accept_mimetypes:
            error_message = {"Error": "Unsupported media type requested by client."}
            return (error_message, 406)

        # Check media type sent by client
        if "application/json" not in request.content_type:
            error_message = {"Error": "Unsupported media type sent by client."}
            return (error_message, 415)

        # If no authorization header is present, return error
        if "authorization" not in request.headers:
            error_message = {"Error": "The request is missing an authorization header."}
            return (error_message, 401)

        # Get and check the authorization header's value
        authorization_header = request.headers.get("authorization")  
        if request_validation.has_valid_auth_header(authorization_header) is False:
            error_message = {"Error": "The request's authorization header value is invalid."}
            return (error_message, 401)  

        # Get and check the validity of the JSON Web Token
        json_web_token = authorization_header[7:]   
        validation_request = requests.Request()
        try:
            jwt_info = id_token.verify_oauth2_token(json_web_token, validation_request, client_id)
        except ValueError:
            error_message = {"Error": "The JWT provided in the request's authorization header is invalid."}
            return (error_message, 401)
        except:
            error_message = {"Error": "The JWT provided in the request's authorization header is invalid."}
            return (error_message, 401)   

        # Check If JWT Is Associated With An Existing User Using Email In JWT
        email = jwt_info["email"]
        user_exists, user_id, user_email = request_validation.email_associated_with_user(email)

        if user_exists is False:
            error_message = {"Error": "The JWT provided in the request's authorization header is not associated with an existing user."}
            return (error_message, 403)  

        trial_key = client.key(constants.trials, int(trial_id))
        trial = client.get(key=trial_key)

        if trial is None:
            error_message = {"Error": "No clinical trial with this ID exists."}
            return (error_message, 404)

        if trial["created_by"]["id"] != user_id:
            error_message = {"Error": "This trial belongs to another user and cannot be edited."}
            return (error_message, 403)

        content = request.get_json()
        attributes = content.keys()

        # Check request body attributes
        possible_attributes = ["public", "name", "phase", "status", "condition", "study_type", "intervention_type", "intervention_name", "companies", "summary", "website"]
        required_attributes = ["public", "name", "phase", "status", "study_type", "intervention_type", "intervention_name", "companies"]
        if not attributes or request_validation.has_valid_attributes(attributes, possible_attributes, required_attributes) is False:
            error_message = {"Error": "A required attribute is missing and/or an extraneous or invalid attribute was provided."}
            return (error_message, 400)

        # Check "name" uniqueness constraint
        if request_validation.is_unique("name", content["name"], constants.trials) is False:
            error_message = {"Error": "A clinical trial with this name already exists."}
            return (error_message, 409)

        # Check if "condition" was erroneously provided
        if "condition" in attributes:
                error_message = {"Error": "Cannot alter the condition associated with a clinical trial using this endpoint."}
                return (error_message, 403)    

        for attribute in attributes:
            trial.update({attribute: content[attribute]}) # TODO: Do this everywhere

        client.put(trial)

        trial["id"] = trial.key.id
        trial["self"] = request.url
        trial["created_by"].update({"self": request.url[:-23] + "users/" + str(user_id)})

        if trial["condition"]:
            trial["condition"].update({"self": request.url[:-23] + "conditions/" + str(trial["condition"]["id"])})

        returned_trial = make_response(json.dumps(trial, indent=4))
        returned_trial.headers.set("Content-Type", "application/json") 
        return (returned_trial, 200)
    
    else:
        return ("Method not recognized", 400)

# Delete a Clinical Trial
@bp.route("/<trial_id>", methods=["DELETE"])
def delete_trial(trial_id):
    if request.method == "DELETE":

        # If no authorization header is present, return error
        if "authorization" not in request.headers:
            error_message = {"Error": "The request is missing an authorization header."}
            return (error_message, 401)

        # Get and check the authorization header's value
        authorization_header = request.headers.get("authorization")  
        if request_validation.has_valid_auth_header(authorization_header) is False:
            error_message = {"Error": "The request's authorization header value is invalid."}
            return (error_message, 401)  

        # Get and check the validity of the JSON Web Token
        json_web_token = authorization_header[7:]   
        validation_request = requests.Request()
        try:
            jwt_info = id_token.verify_oauth2_token(json_web_token, validation_request, client_id)
        except ValueError:
            error_message = {"Error": "The JWT provided in the request's authorization header is invalid."}
            return (error_message, 401)
        except:
            error_message = {"Error": "The JWT provided in the request's authorization header is invalid."}
            return (error_message, 401)   

        # Check If JWT Is Associated With An Existing User Using Email In JWT
        email = jwt_info["email"]
        user_exists, user_id, user_email = request_validation.email_associated_with_user(email)

        if user_exists is False:
            error_message = {"Error": "The JWT provided in the request's authorization header is not associated with an existing user."}
            return (error_message, 403)

        trial_key = client.key(constants.trials, int(trial_id))
        trial = client.get(key=trial_key)

        if trial is None:
            error_message = {"Error": "No clinical trial with this ID exists."}
            return (error_message, 404)

        if trial["created_by"]["id"] != user_id:
            error_message = {"Error": "This trial belongs to another user and cannot be deleted."}
            return (error_message, 403)

        # If Trial Is Associated With A Condition, Remove It From Condition
        if trial["condition"]:
            condition_id = trial["condition"]["id"]
            condition_key = client.key(constants.conditions, int(condition_id))
            condition = client.get(key=condition_key)
            condition["clinical_trials"].remove({"id": trial.key.id})

        client.delete(trial_key)
        return ("", 204)

    else:
        return ("Method not recognized", 400)

# Edit The Condition Associated With A Clinical Trial
@bp.route("/<trial_id>/conditions/<condition_id>", methods=["PUT"])
def put_trial_condition(trial_id, condition_id):
        
    if request.method == "PUT":

        # Check media type requested by client
        if "application/json" not in request.accept_mimetypes:
            error_message = {"Error": "Unsupported media type requested by client."}
            return (error_message, 406)

        # If no authorization header is present, return error
        if "authorization" not in request.headers:
            error_message = {"Error": "The request is missing an authorization header."}
            return (error_message, 401)

        # Get and check the authorization header's value
        authorization_header = request.headers.get("authorization")  
        if request_validation.has_valid_auth_header(authorization_header) is False:
            error_message = {"Error": "The request's authorization header value is invalid."}
            return (error_message, 401)  

        # Get and check the validity of the JSON Web Token
        json_web_token = authorization_header[7:]   
        validation_request = requests.Request()
        try:
            jwt_info = id_token.verify_oauth2_token(json_web_token, validation_request, client_id)
        except ValueError:
            error_message = {"Error": "The JWT provided in the request's authorization header is invalid."}
            return (error_message, 401)
        except:
            error_message = {"Error": "The JWT provided in the request's authorization header is invalid."}
            return (error_message, 401)   

        # Check If JWT Is Associated With An Existing User Using Email In JWT
        email = jwt_info["email"]
        user_exists, user_id, user_email = request_validation.email_associated_with_user(email)

        if user_exists is False:
            error_message = {"Error": "The JWT provided in the request's authorization header is not associated with an existing user."}
            return (error_message, 403)  

        trial_key = client.key(constants.trials, int(trial_id))
        trial = client.get(key=trial_key)

        if trial is None:
            error_message = {"Error": "No clinical trial with this ID exists."}
            return (error_message, 404)

        if trial["created_by"]["id"] != user_id:
            error_message = {"Error": "This trial belongs to another user and cannot be edited."}
            return (error_message, 403)

        condition_key = client.key(constants.conditions, int(condition_id))
        condition = client.get(key=condition_key)
        
        if condition is None:
            error_message = {"Error": "No condition with this ID exists."}
            return (error_message, 404)

        # Update Trial And Condition
        trial.update({"condition": {"id": condition_id}})
        condition["clinical_trials"].append({"id": trial.key.id})
        client.put(trial)
        client.put(condition)

        # Return Trial
        trial["id"] = trial.key.id
        trial["self"] = request.url[:-44] + str(trial.key.id)
        trial["created_by"].update({"self": request.url[:-51] + "users/" + str(user_id)})
        trial["condition"].update({"self": request.url[:-51] + "conditions/" + str(trial["condition"]["id"])})

        returned_trial = make_response(json.dumps(trial, indent=4))
        returned_trial.headers.set("Content-Type", "application/json") 
        return (returned_trial, 200)
    
    else:
        return ("Method not recognized", 400)

# Remove The Condition Associated With A Clinical Trial
@bp.route("/<trial_id>/conditions/<condition_id>", methods=["DELETE"])
def delete_trial_condition(trial_id, condition_id):
    
    if request.method == "DELETE":

        # Check media type requested by client
        if "application/json" not in request.accept_mimetypes:
            error_message = {"Error": "Unsupported media type requested by client."}
            return (error_message, 406)

        # If no authorization header is present, return error
        if "authorization" not in request.headers:
            error_message = {"Error": "The request is missing an authorization header."}
            return (error_message, 401)

        # Get and check the authorization header's value
        authorization_header = request.headers.get("authorization")  
        if request_validation.has_valid_auth_header(authorization_header) is False:
            error_message = {"Error": "The request's authorization header value is invalid."}
            return (error_message, 401)  

        # Get and check the validity of the JSON Web Token
        json_web_token = authorization_header[7:]   
        validation_request = requests.Request()
        try:
            jwt_info = id_token.verify_oauth2_token(json_web_token, validation_request, client_id)
        except ValueError:
            error_message = {"Error": "The JWT provided in the request's authorization header is invalid."}
            return (error_message, 401)
        except:
            error_message = {"Error": "The JWT provided in the request's authorization header is invalid."}
            return (error_message, 401)   

        # Check If JWT Is Associated With An Existing User Using Email In JWT
        email = jwt_info["email"]
        user_exists, user_id, user_email = request_validation.email_associated_with_user(email)

        if user_exists is False:
            error_message = {"Error": "The JWT provided in the request's authorization header is not associated with an existing user."}
            return (error_message, 403)  

        trial_key = client.key(constants.trials, int(trial_id))
        trial = client.get(key=trial_key)

        if trial is None:
            error_message = {"Error": "No clinical trial with this ID exists."}
            return (error_message, 404)

        if trial["created_by"]["id"] != user_id:
            error_message = {"Error": "This trial belongs to another user and cannot be edited."}
            return (error_message, 403)

        condition_key = client.key(constants.conditions, int(condition_id))
        condition = client.get(key=condition_key)
        
        if condition is None:
            error_message = {"Error": "No condition with this ID exists."}
            return (error_message, 404)

        # Update Trial And Condition
        trial.update({"condition": {}})
        #condition["clinical_trials"].remove({"id": trial.key.id})
        for current_trial in condition["clinical_trials"]:
            print(current_trial)
            if current_trial["id"] == trial.key.id:
                condition["clinical_trials"].remove(current_trial)
                break

        client.put(trial)
        client.put(condition)

        # Return Trial
        trial["id"] = trial.key.id
        trial["self"] = request.url[:-44] + str(trial.key.id)
        trial["created_by"].update({"self": request.url[:-51] + "users/" + str(user_id)})

        returned_trial = make_response(json.dumps(trial, indent=4))
        returned_trial.headers.set("Content-Type", "application/json") 
        return (returned_trial, 200)
    
    else:
        return ("Method not recognized", 400)

# Method Not Allowed
@bp.route("/<trial_id>", methods=["POST"])
def post_trial_not_allowed(trial_id):
    
    if request.method == "POST":

        error_message = {"Error": "Cannot POST to this endpoint."}
        return (error_message, 405)
    
    else:
        return ("Method not recognized", 400)
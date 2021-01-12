from google.cloud import datastore
import constants

client = datastore.Client(project="clinical-trials-link")

def is_unique(key, value, kind):
    query = client.query(kind=kind)
    results = list(query.fetch())

    for item in results:
        if item[key] == value:
            return False

    return True

def has_valid_attributes(provided_attributes, possible_attributes, required_attributes=[]):
    for attribute in required_attributes:
        if attribute not in provided_attributes:
            return False
    for attribute in provided_attributes:
        if attribute not in possible_attributes:
            return False

    return True

def has_valid_auth_header(authorization_header):
    if authorization_header == "" or authorization_header[0:7] != "Bearer " or len(authorization_header) < 20:
        return False
    
    return True

def email_associated_with_user(email):

    user_exists = False
    user_id = None
    user_email = None

    # Get All Current Users
    user_query = client.query(kind=constants.users)
    user_results = list(user_query.fetch())
        
    # Check If User Account With Email Already Exists
    for user in user_results:
        if user["email"] == email:
            user_exists = True
            user_id = user.key.id
            user_email = user["email"]
            break

    return (user_exists, user_id, user_email)

def condition_exists(name):

    condition_exists = False
    condition_id = None
    condition_name = None

    # Check to see if provided condition exists
    query = client.query(kind=constants.conditions)
    results = list(query.fetch())

    for condition in results:
        if condition["name"] == name:
            condition_exists = True
            condition_id = condition.key.id
            condition_name = condition["name"]
            break

    return (condition_exists, condition_id, condition_name)

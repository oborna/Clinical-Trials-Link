from google.cloud import datastore
from flask import Blueprint, request, redirect, url_for, render_template
import json
import constants

# Authentication and Authorization
# Documentation: https://requests-oauthlib.readthedocs.io/en/latest/oauth2_workflow.html
from requests_oauthlib import OAuth2Session
from google.oauth2 import id_token
from google.auth import crypt
from google.auth import jwt
from google.auth.transport import requests

client = datastore.Client(project="clinical-trials-link")
bp = Blueprint("auth", __name__, url_prefix="/auth")

# OAuth 2.0 Variables
client_id = r"394192668733-f86tkpt35f403k7oiidoabdaldc1dp9r.apps.googleusercontent.com"
client_secret = r"0wQqw5I830h5gdObbbt1tizf"
redirect_uri = "https://clinical-trials-link.wn.r.appspot.com/auth/oauth2callback"
#redirect_uri = "http://localhost:8080/auth/oauth2callback"
scope = ["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile", "openid"]

oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)

# Google OAuth2.0
@bp.route("/oauth2")
def oauth2():
    
    google_oauth2_url = "https://accounts.google.com/o/oauth2/v2/auth"
    authorization_url, state = oauth.authorization_url(google_oauth2_url, access_type="offline", prompt="select_account")
    
    return redirect(authorization_url)

# Google OAuth2.0 Callback
@bp.route("/oauth2callback")
def oauth2callback():
    # Exchange Authorization Code For Access Token
    google_oauth2_exchange_token_url = "https://accounts.google.com/o/oauth2/token"
    token = oauth.fetch_token(google_oauth2_exchange_token_url, authorization_response=request.url, client_secret=client_secret)
    req = requests.Request()
    print(token)

    # Verify And Save JSON Web Token
    id_info = id_token.verify_oauth2_token(token["id_token"], req, client_id)
    jwt = token["id_token"]

    # Get Google User's Information
    google_user_info = oauth.get("https://www.googleapis.com/oauth2/v1/userinfo")
    google_user_info_json = google_user_info.json()
    first_name = google_user_info_json["given_name"]
    last_name = google_user_info_json["family_name"]
    email = google_user_info_json["email"]
    clinical_trials = []

    account_exists = False

    # Get All Current Users
    user_query = client.query(kind=constants.users)
    user_results = list(user_query.fetch())
    
    # Check If User Account Already Exists By Email
    for user in user_results:
        if user["email"] == email:
            account_exists = True   # TODO: Check if user information needs to be updated
            user_id = user.key.id
            break

    # If User Does Not Exist, Create New User And Display Account Information
    if account_exists is False:
        new_user = datastore.entity.Entity(key=client.key(constants.users))
        new_user.update({"first_name": first_name, "last_name": last_name, "email": email, "clinical_trials": []}) # TODO: Add access token, refresh token?
        client.put(new_user)
        user_id = new_user.key.id
        header = "Account Created"
        message = "Your account has been created. Its information can be viewed below."
    # Otherwise, Display Current User Account Information
    else:
        header = "Account Found"
        message = "An account already exists for this email. Its information can be viewed below."

    return render_template("user_account.html", header=header, message=message, user_id=user_id, first_name=first_name, last_name=last_name, email=email, jwt=jwt)

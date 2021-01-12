import os
from flask import Flask, request, render_template, session, redirect, url_for
from google.cloud import datastore
import json

# Constants & Blueprints
import constants
import auth
import users
import conditions
import trials

app = Flask(__name__)
client = datastore.Client(project="clinical-trials-link")

# Registered Blueprints
app.register_blueprint(auth.bp)
app.register_blueprint(users.bp)
app.register_blueprint(conditions.bp)
app.register_blueprint(trials.bp)

# Route Handler For Index Page
@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html")

# Route Handler For Documentation Page
@app.route("/documentation")
def documentation():

    # Get data models
    with open("templates/methods/data_models.json", "r") as f:
        data_models = json.load(f)
        f.close()

    # Get trial methods
    with open("templates/methods/trials.json", "r") as f:
        trial_methods = json.load(f)
        f.close()

    # Get condition methods
    with open("templates/methods/conditions.json", "r") as f:
        condition_methods = json.load(f)
        f.close()

    return render_template("documentation.html", data_models = data_models, trial_methods = trial_methods, condition_methods = condition_methods)

if __name__ == "__main__":
    # ACTION ITEM: 
    #       Disable when running in production.
    #os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
    app.run(host="127.0.0.1", port=8080, debug=True)
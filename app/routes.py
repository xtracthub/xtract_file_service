from flask_login import current_user
from app.models import generate_user, check_login
from app import app, db
from flask import request, session, g
import json


@app.before_request
def before_request():
    g.user = None
    if 'username' in session:
        g.user = session['username']


@app.route('/')
def index():
    return "blah"


@app.route('/create_user', methods=['POST'])
def create_user():
    try:
        user_json = json.loads(request.get_data())
        username = user_json['Username']
        email = user_json['Email']
        password = user_json['Password']
    except:
        return "Incorrect json format, please format to '{\"Username\": \"your_username\", \"Email\": \"your_email\"," \
               "\"Password\": \"your_password\"}"

    try:
        db.create_all()
        db.session.add(generate_user(username, email, password))
        db.session.commit()
    except:
        return "Username already exists"

    return "Successfully registered {}".format(username)


@app.route('/login', methods=['GET', 'POST'])
def login():
    #return str(current_user.is_authenticated)
    if current_user.is_authenticated:
        return "Already logged in"

    try:
        user_json = json.loads(request.get_data())
        username = user_json['Username']
        password = user_json['Password']
    except:
        return "Incorrect json format, please format to '{\"Username\": \"your_username\", \"Password\": \"your_password\"}"

    user = check_login(username, password)
    session['username'] = user.username

    if user is None:
        return "Invalid username or password"

    return session['username']
    #return "Successfully logged in {}".format(username)


@app.route('/test', methods=['GET'])
def blah():
    if 'username' in session:
        return session['username']
    else:
        return "Failed"




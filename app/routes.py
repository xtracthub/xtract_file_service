from flask_login import current_user
from app.models import generate_user, check_login, User
from app import app, db
from flask import request, session, g
from werkzeug.utils import secure_filename
import json
import os

db.create_all()


@app.before_request
def before_request():
    g.uuid = '18ae0cd4-2883-420f-8843-78adcf4d38dd'
    if 'username' in session:
        #g.uuid = User.query.filter_by(username=session['username']).first().user_uuid
        g.uuid = '18ae0cd4-2883-420f-8843-78adcf4d38dd'


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

    if User.query.filter_by(username=username).first() is None:
        db.session.add(generate_user(username, email, password))
        db.session.commit()
    else:
        return "Username already exists"

    return "Successfully registered {}".format(username)


@app.route('/login', methods=['GET', 'POST'])
def login():
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


@app.route('/files', methods=['GET', 'POST', 'DELETE'])
def user_file_handler():
    if g.uuid:
        if request.method == 'GET':
            file_list_str = ""
            if len(os.listdir('xtract_user_data/{}'.format(g.uuid))) > 0:
                for file_name in os.listdir('xtract_user_data/{}'.format(g.uuid)):
                    file_list_str += file_name + " {}GB\n".format(os.path.getsize(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'],
                                                                                                            g.uuid), file_name)) / (10 ** 9))
            else:
                return "You have no files"
            return file_list_str

        elif request.method == 'POST':
            if 'file' not in request.files:
                return "No file"
            file = request.files['file']

            if file.filename == '':
                return "No file selected"

            if secure_filename(file.filename) is not '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], g.uuid), filename))
                return "Successfully saved {}".format(filename)
            else:
                return "Bad file name"

        elif request.method == 'DELETE':
            filename = request.get_data().decode('utf-8')
            if os.path.exists(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], g.uuid), filename)):
                os.remove(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], g.uuid), filename))
                return "Sucessfully removed {}".format(filename)
            else:
                return "File does not exist"










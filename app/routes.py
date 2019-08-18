from app.models import generate_user, check_login, User
from app import app, db
from flask import request, session, g
from werkzeug.utils import secure_filename
from app.docker_handler import extract_metadata
import json
import os

db.create_all()


@app.route('/')
def index():
    return "blah"


# Example curl:
# curl -X post -d '{"Username": "example", "Email": "example@gmail.com", "Password": "password"}' http://127.0.0.1/create_user
@app.route('/create_user', methods=['POST'])
def create_user():
    """Creates a user within the SQL database given a json with a Username, Email, and Password.

    Parameter:
    (json): json in the format '{"Username": "", "Email": "", "Password": ""}' passed through -d from curl.

    Return:
    (str): A success or failure message.
    """
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


# Example curl:
# curl -X get -d '{"Username": "example", "Password": "password"}' http://127.0.0.1:5000/login
@app.route('/login', methods=['GET'])
def login():
    """Returns a user id when provided with correct credentials.

    Parameter:
    (json): json in for the format '{"Username": "", "Password": ""} passed through -d from curl.

    Return:
    (str): Returns message containing user id that must be used to view files.
    """
    try:
        user_json = json.loads(request.get_data())
        username = user_json['Username']
        password = user_json['Password']
    except:
        return "Incorrect json format, please format to '{\"Username\": \"your_username\", \"Password\": \"your_password\"}"

    user = check_login(username, password)
    g.user_uuid = user.user_uuid

    return "User unique id: {}".format(user.user_uuid)


@app.route('/test', methods=['GET', 'POST'])
def blah():
    if 'username' in session:
        return session['username']
    else:
        return "Failed"


# Example curl:
# curl -X get -H "Authentication: blah" http://127.0.0.1:5000/files
# curl -X post -H "Authentication: blah" -F "file=@/local/file/path.txt" http://127.0.0.1:5000/files
# curl -X delete -H "Authentication: blah" -d filename http://127.0.0.1:5000/files
@app.route('/files', methods=['GET', 'POST', 'DELETE'])
def user_file_handler():
    """Allows users to view uploaded file information, upload files, and delete files
    given that they provide correct authentication.
    """
    authentication = request.headers.get('Authentication')

    if User.query.filter_by(user_uuid=authentication).first() is not None:
        if request.method == 'GET':
            file_list_str = ""
            if len(os.listdir('xtract_user_data/{}'.format(authentication))) > 0:
                for file_name in os.listdir('xtract_user_data/{}'.format(authentication)):
                    file_list_str += file_name + " {}GB\n".format(os.path.getsize(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'],
                                                                                                            authentication), file_name)) / (10 ** 9))
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
                file.save(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], authentication), filename))
                return "Successfully saved {}".format(filename)
            else:
                return "Bad file name"

        elif request.method == 'DELETE':
            filename = request.get_data().decode('utf-8')
            if os.path.exists(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], authentication), filename)):
                os.remove(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], authentication), filename))
                return "Sucessfully removed {}".format(filename)
            else:
                return "File does not exist"

    else:
        return "Invalid credentials"


# Example curl:
# curl -X get -H "Authentication: blah" -d '{"Filename": "blah.csv", "Extractor": "tabular"}' http://127.0.0.1:5000/metadata
@app.route('/metadata', methods=["GET"])
def user_metadata_handler():
    authentication = request.headers.get('Authentication')
    extractor_names = ['tabular', 'jsonxml', 'netcdf', 'keyword', 'image', 'maps', 'matio']

    if User.query.filter_by(user_uuid=authentication).first() is not None:
        if request.method == "GET":
            try:
                user_json = json.loads(request.get_data())
                filename = user_json['Filename']
                extractor = user_json['Extractor']
            except:
                return "Incorrect json format, please format to '{\"Filename\": \"file_name\", \"Extractor\": \"extractor\"}"

            if extractor in extractor_names:
                if filename in os.listdir('xtract_user_data/{}'.format(authentication)):
                    file_path = 'xtract_user_data/{}/{}'.format(authentication, filename)

                    return extract_metadata(extractor, file_path)
                else:
                    return "File has not been uploaded"
            else:
                return "Invalid extractor name. Valid extractors are {}".format(", ".join(extractor_names))

    else:
        return "Invalid credentials"










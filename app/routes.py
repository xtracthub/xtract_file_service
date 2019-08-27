from app.models import generate_user, check_login, User, remove_user_data, FileMetadata
from app.docker_handler import build_all_images
from app import app, db
from flask import request
from werkzeug.utils import secure_filename
from app.metadata_handler import delete_user_metadata, extract_user_metadata
from app.decompressor import is_compressed, recursive_compression
from flask import flash
import json
import os

extractor_names = ['tabular', 'jsonxml', 'netcdf', 'keyword', 'image', 'maps', 'matio']


@app.before_first_request
def startup_funcs():
    """A function that will prep the flask server for our use case."""
    import time
    t0 = time.time()
    db.create_all()
    build_all_images(multiprocess=True)

    try:
        os.mkdir('xtract_user_data')
    except:
        pass

    print("Setup took: {} seconds".format(time.time() - t0))


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
               "\"Password\": \"your_password\"}\n"

    if User.query.filter_by(username=username).first() is None:
        db.session.add(generate_user(username, email, password))
        db.session.commit()
    else:
        return "Username already exists\n"

    return "Successfully registered {}\n".format(username)


# Example curl:
# curl -X delete -H "Authentication: blah" -d '{"Username": "example", "Password": "password"}' http://127.0.0.1:5000/delete_user
@app.route('/delete_user', methods=['DELETE'])
def delete_user():
    """Deletes a user within the SQL database.

    Parameters:
    (json): json in the format of '{"Username": "", "Password": ""} passed through -d from curl for the user to be deleted.
    (str): String in the format of "Authentication: " with the user id returned from login().
    """
    authentication = request.headers.get('Authentication')

    try:
        user_json = json.loads(request.get_data())
        username = user_json['Username']
        password = user_json['Password']

        user = check_login(username, password)
    except:
        return "Incorrect json format, please format to '{\"Username\": \"your_username\", \"Password\": \"your_password\"}\n"

    if user.user_uuid == authentication:
        remove_user_data(user)

        return "Successfully deleted {}\n".format(username)
    else:
        return "Authentication does not match credentials\n"


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
        return "Incorrect json format, please format to '{\"Username\": \"your_username\", \"Password\": \"your_password\"}\n"

    user = check_login(username, password)

    if user is None:
        return "Incorrect login\n"
    else:
        return "User unique id: {}\n".format(user.user_uuid)


# Example curl:
# curl -X get -H "Authentication: blah" http://127.0.0.1:5000/files
# curl -X post -H "Authentication: blah" -H "Extractor: blah" -F "file=@/local/file/path.txt" http://127.0.0.1:5000/files
# curl -X delete -H "Authentication: blah" -d filename http://127.0.0.1:5000/files
@app.route('/files', methods=['GET', 'POST', 'DELETE'])
def user_file_handler():
    """Allows users to view uploaded file information, upload files for metadata
    extraction, and delete files given that they provide correct authentication.

    Parameters:
    (str): String with authentication returned from login() in the format "Authentication: your_authentication"
    passed through -H using curl.
    (str): String with extractor name if method is POST in the format "Extractor: extractor_name" passed through -H
    using curl.
    (str): Name of file to delete if method is DELETE passed through -d using curl.
    """
    authentication = request.headers.get('Authentication')

    if User.query.filter_by(user_uuid=authentication).first() is not None:
        if request.method == 'GET':
            file_list_str = ""
            if len(os.listdir('xtract_user_data/{}'.format(authentication))) > 0:
                for path, subdirs, files in os.walk('xtract_user_data/{}'.format(authentication)):
                    for name in files:
                        file_path = os.path.join(path, name)
                        file_list_str += file_path[file_path.index(authentication) + len(authentication):] \
                                         + " {} MB\n".format(os.path.getsize(file_path) / 10 ** 6)
            else:
                return "You have no files\n"

            return file_list_str

        elif request.method == 'POST':
            if 'file' not in request.files:
                return "No file\n"
            file = request.files['file']

            if file.filename == '':
                return "No file selected\n"

            if secure_filename(file.filename) in os.listdir('xtract_user_data/{}'.format(authentication)):
                return "{} already exists\n".format(secure_filename(file.filename))
            elif secure_filename(file.filename) is not '':
                filename = secure_filename(file.filename)
                file_path = "xtract_user_data/{}/{}".format(authentication, filename)
                extractor = request.headers.get("Extractor").lower() if request.headers.get("Extractor") is not None else ""
                file.save(file_path)

                if is_compressed(file_path):
                    recursive_compression(file_path, "xtract_user_data/{}".format(authentication))

                if extractor not in extractor_names:
                    return "File successfully uploaded, but extractor does not exist\n"

                task = extract_user_metadata.apply_async(args=[file_path, authentication, extractor],
                                                         time_limit=10)

                return "Processing metadata at task id {}. Go to /tasksto view task status\n".format(task.id)
            else:
                return "Bad file name\n"

        elif request.method == 'DELETE':
            filename = request.get_data().decode('utf-8')
            if os.path.exists(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], authentication), filename)):
                os.remove("xtract_user_data/{}/{}".format(authentication, filename))
                delete_user_metadata("xtract_user_data/{}/{}".format(authentication, filename), authentication)

                return "Sucessfully removed {} and associated metadata\n".format(filename)
            else:
                return "File does not exist\n"

    else:
        return "Invalid credentials\n"


# Example curl:
# curl -X get -H "Authentication: blah" -d filename http://127.0.0.1:5000/metadata
# curl -X post -H "Authentication: blah" -d '{"Filename": "blah", "Extractor": "blah"}' http://127.0.0.1:5000/metadata
# curl -X delete -H "Authentication: blah" -d filename http://127.0.0.1:5000/metadata
@app.route('/metadata', methods=["GET", "POST", "DELETE"])
def user_metadata_handler():
    """Allows user to view their metadata, extract metadata for files that are already uploaded,
    or delete metadata.

    Parameters:
    (str): String with authentication returned from login() in the format "Authentication: your_authentication"
    passed through -H using curl.
    (str): String with filename of metadata to view in the format "Filename: file_name" passed through -H using
    curl if method is GET.
    (json): json in the format of '{"Filename": "", "Extractor": ""} passed through -d from curl for the file to
    extract metadata from as well as the extractor to use if method is POST.
    (str): Name of file to delete metadata for passed through -d from curl if the method is delete.
    """
    authentication = request.headers.get('Authentication')

    if User.query.filter_by(user_uuid=authentication).first() is not None:
        if request.method == "GET":
            metadata_string = ""
            file_name = request.get_data().decode('utf-8')
            file_path = "xtract_user_data/{}/{}".format(authentication, file_name)

            for metadata in FileMetadata.query.filter_by(file_path=file_path, user_uuid=authentication).all():
                metadata_string += "{} ({}): {}\n".format(file_name, metadata.extractor, metadata.metadata_dict)

            if metadata_string == "":
                return "Metadata does not exist\n"
            else:
                return metadata_string
        elif request.method == "POST":
            try:
                extraction_json = json.loads(request.get_data())
                file_name = extraction_json['Filename']
                extractor = extraction_json['Extractor'].lower()

                if extractor not in extractor_names:
                    return "Extractor does not exist\n"
            except:
                return "Incorrect json format, please format to '{\"Filename\": \"your_file\", \"Extractor\": \"extractor_name\"}'\n"

            file_path = "xtract_user_data/{}/{}".format(authentication, file_name)
            if FileMetadata.query.filter_by(file_path=file_path, extractor=extractor).first() is None:
                task = extract_user_metadata.apply_async(args=[file_path, authentication, extractor],
                                                         soft_time_limit=10)

                return "Processing metadata at task id {}. Go to /tasks to view task status\n".format(task.id)
            else:
                return "Already processed metadata for this extractor file combo\n"
        elif request.method == "DELETE":
            file_name = request.get_data().decode('utf-8')
            file_path = "xtract_user_data/{}/{}".format(authentication, file_name)
            return delete_user_metadata(file_path, authentication)

    else:
        return "Invalid credentials\n"


# Example curl:
# curl -X get -d task_id http://127.0.0.1:5000/tasks
@app.route('/tasks', methods=['GET', 'POST'])
def user_task_handler():
    """Returns the status of a task.

    Parameter:
    (str): Task ID returned by user_metadata_handler() or user_file_handler()
    """
    task_id = request.get_data()
    task = extract_user_metadata.AsyncResult(task_id)

    if task.state == "SUCCESS":
        return "Metadata processing has been completed, go to /metadata to view results\n"
    elif task.state == "PENDING" or "RETRY":
        return "Task has not been completed yet, check back later\n"
    elif task.state == "FAILURE":
        return "Task failed"


@app.route('/')
def blah():
    return "blah"

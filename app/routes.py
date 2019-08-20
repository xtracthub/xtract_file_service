from app.models import generate_user, check_login, User, remove_user_data, FileMetadata
from app import app, db, celery
from flask import request
from werkzeug.utils import secure_filename
from app.docker_handler import extract_metadata
import json
import os

db.create_all()


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
                for file_name in os.listdir('xtract_user_data/{}'.format(authentication)):
                    file_list_str += file_name \
                                     + " {}GB\n".format(os.path.getsize("xtract_user_data/{}/{}".format(authentication,
                                                                                                        file_name)) / (10 ** 9))
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
                file.save("xtract_user_data/{}/{}".format(authentication, filename))
                extractor = request.headers.get("Extractor")

                task = extract_user_metadata.delay("xtract_user_data/{}/{}".format(authentication, filename),
                                                   authentication, extractor)

                return "Processing metadata at task id {}. Go to /tasks/<task_id> to view task status\n".format(task.id)
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


@celery.task
def extract_user_metadata(file_path, authentication, extractor):
    """Extracts metadata from a file and writes a FileMetadata objeect to the SQL server.

    Parameters:
    file_path (str): File path of file to extract metadata from.
    authentication (str): User authentication as returned by login().
    extractor (str): Name of extractor to use to extract metadata.
    """
    extractor_names = ['tabular', 'jsonxml', 'netcdf', 'keyword', 'image', 'maps', 'matio']
    if extractor not in extractor_names:
        return "Incorrect extractor name\n"

    metadata_dict = extract_metadata(extractor, file_path)
    user = User.query.filter_by(user_uuid=authentication).first()
    file_metadata = FileMetadata(file_path=file_path, metadata_dict=metadata_dict, user=user, extractor=extractor)
    db.session.add(file_metadata)
    db.session.commit()
    return metadata_dict


def delete_user_metadata(file_path, authentication):
    """Deletes a users metadata for a given file.

    Parameters:
    file_path (str): File path of metadata to delete.
    authentication (str): User authentication as returned by login().
    """
    metadata_to_delete = FileMetadata.query.filter_by(file_path=file_path, user_uuid=authentication).all()

    if len(metadata_to_delete) == 0:
        return "Metadata for {} does not exist".format(os.path.basename(file_path))
    else:
        for metadata in metadata_to_delete:
            db.session.delete(metadata)
        db.session.commit()

        return "Successfully deleted metadata for {}".format(os.path.basename(file_path))



# Example curl:
# curl -X get -H "Authentication: blah" -H "Filename: blah" http://127.0.0.1:5000/metadata
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
            file_name = request.headers.get("Filename")
            file_path = "xtract_user_data/{}/{}".format(authentication, file_name)

            for metadata in FileMetadata.query.filter_by(file_path=file_path, user_uuid=authentication).all():
                metadata_string += "{} ({}): {}\n".format(file_name, metadata.extractor, metadata.metadata_dict)

            return metadata_string
        elif request.method == "POST":
            try:
                extraction_json = json.loads(request.get_data())
                file_name = extraction_json['Filename']
                extractor = extraction_json['Extractor']
            except:
                return "Incorrect json format, please format to '{\"Filename\": \"your_file\", \"Extractor\": \"extractor_name\"}\n"

            file_path = "xtract_user_data/{}/{}".format(authentication, file_name)
            if FileMetadata.query.filter_by(file_path=file_path, extractor=extractor).first() is None:
                task = extract_user_metadata.delay("xtract_user_data/{}/{}".format(authentication, file_name),
                                                   authentication, extractor)

                return "Processing metadata at task id {}. Go to /tasks/<task_id> to view task status\n".format(task.id)
            else:
                return "Already processed metadata for this extractor file combo\n"
        elif request.method == "DELETE":
            file_name = request.headers.get("Filename")
            file_path = "xtract_user_data/{}/{}".format(authentication, file_name)
            return delete_user_metadata(file_path, authentication)


    else:
        return "Invalid credentials\n"


# Example curl:
# curl -X get -d task_id http://127.0.0.1:5000/tasks/
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
    else:
        return "Task has not been completed yet, check back later\n"


@app.route('/')
def blah():
    i = celery.control.inspect()
    return str(i.registered())










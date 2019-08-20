from app import db
import hashlib
import uuid
import os
import shutil


def pass_hasher(password):
    hashed_str = hashlib.md5(password.encode('utf-8')).hexdigest()

    return hashed_str


class User(db.Model):
    """User class.

    id (int): ID for each user, automatically generated.
    username (str): Username of user.
    email (str): Email of user.
    password_hash (str): The user's hashed password.
    user_metadata (list): FileMetadata objects associated with the user.
    """
    id = db.Column(db.Integer, primary_key=True, unique=False)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=False)
    password_hash = db.Column(db.String(128))
    user_uuid = db.Column(db.String, index=True)
    user_metadata = db.relationship('FileMetadata', backref='user', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)


def generate_user(username, email, password):
    """Generates a User class object.

    Parameters:
    username (str): Username of user.
    email (str): Email of user.
    password (str): Password of user (password will be hashed before being
    passed to the User class object).

    Return:
    (User class object): Returns a User class object.
    """
    user_uuid = str(uuid.uuid4())
    os.mkdir('xtract_user_data/{}'.format(user_uuid))

    return User(username=username, email=email, password_hash=pass_hasher(password), user_uuid=user_uuid)


def remove_user_data(user):
    """Deletes a users data from the SQL database as well as their associated files.

    :param user:
    :return:
    """
    shutil.rmtree('xtract_user_data/{}'.format(user.user_uuid))

    db.session.delete(user)
    db.session.commit()

    return "Successfully deleted user"


def check_login(username, password):
    return User.query.filter_by(username=username, password_hash=pass_hasher(password)).first()


class FileMetadata(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=False)
    user_uuid = db.Column(db.String, db.ForeignKey('user.user_uuid'))
    file_path = db.Column(db.String, index=True, unique=False)
    metadata_dict = db.Column(db.String, index=True, unique=False)
    extractor = db.Column(db.String, index=True)





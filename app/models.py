from app import db
import hashlib
from flask_login import UserMixin
import uuid
import os


def pass_hasher(password):
    hashed_str = hashlib.md5(password.encode('utf-8')).hexdigest()

    return hashed_str


class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True, unique=False)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=False)
    password_hash = db.Column(db.String(128))
    user_uuid = db.Column(db.String, index=True)

    def __repr__(self):
        return '<User {}>'.format(self.username)


def generate_user(username, email, password):
    user_uuid = str(uuid.uuid4())
    os.mkdir('xtract_user_data/{}'.format(user_uuid))

    return User(username=username, email=email, password_hash=pass_hasher(password), user_uuid=user_uuid)


def check_login(username, password):
    return User.query.filter_by(username=username, password_hash=pass_hasher(password)).first()


def load_user(id):
    return User.query.get(int(id))


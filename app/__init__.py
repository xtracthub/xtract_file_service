from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from app.docker_handler import build_all_images
import os

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

try:
    os.mkdir('xtract_user_data')
except:
    pass

build_all_images(multiprocess=False)

from app import routes, models
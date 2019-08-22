from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from app.docker_handler import build_all_images
from celery import Celery

app = Flask(__name__)
app.config.from_object(Config)
celery_app = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery_app.conf.update(app.config)
# argv = ["worker"]
# celery_app.worker_main(argv=argv)
db = SQLAlchemy(app)


from app import routes, models
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# TODO: Move this into some sort of config file or database
PATH_STORAGE = '/home/v_malarik/dev/gs-manager/instance/docker_storage'

db = SQLAlchemy()
migrate = Migrate()

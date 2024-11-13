"""Flask configuration."""
from os import environ, path

basedir = path.abspath(path.dirname(__file__))


class Config(object):
    """Base config."""
    SECRET_KEY = "dev"
    STATIC_FOLDER = 'static'
    TEMPLATES_FOLDER = 'templates'


class ProductionConfig(Config):
    """Production config."""
    FLASK_ENV = "production"
    FLASK_DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///var/tmp/gs_manager/gsmanager.sqlite"
    GS_PATH_STORAGE = '/var/tmp/gs-manager/docker_storage'

class DevelopmentConfig(Config):
    """Development config."""
    FLASK_ENV = "development"
    FLASK_DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///var/tmp/gs_manager/gsmanager.sqlite"
    GS_PATH_STORAGE = '/var/tmp/gs-manager/docker_storage'

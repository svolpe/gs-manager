"""Flask configuration."""
from os import environ, path

basedir = path.abspath(path.dirname(__file__))


class Config(object):
    """Base config."""
    SECRET_KEY = "dev"
    STATIC_FOLDER = 'static'
    TEMPLATES_FOLDER = 'templates'
    
    # SQLALCHEMY_ENGINE_OPTIONS lets you set connection options. The example below increases the timeout
    # in order to reduce write timeout errors
    SQLALCHEMY_ENGINE_OPTIONS = { 'connect_args': { 'timeout': 10 }}

class ProductionConfig(Config):
    """Production config."""
    FLASK_ENV = "production"
    FLASK_DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///gsmanager.sqlite"
    GS_PATH_STORAGE = '/var/tmp/gs-manager/docker_storage'
    SQLALCHEMY_POOL_SIZE = 50

class DevelopmentConfig(Config):
    """Development config."""
    FLASK_ENV = "development"
    FLASK_DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///gsmanager.sqlite"
    GS_PATH_STORAGE = '/var/tmp/gs-manager/docker_storage'
    SQLALCHEMY_POOL_SIZE = 50

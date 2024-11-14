"""nwnee backend configuration."""
from os import environ, path

basedir = path.abspath(path.dirname(__file__))


class Config(object):
    """Base config."""
    GS_MANAGER_DATABASE_URI = 'instance/gsmanager.sqlite'
    DOCKER_IMAGE = 'nwnxee/unified'
    DOCKER_NETWORK = 'host'

class ProductionConfig(Config):
    """Production config."""
    nwnx_sql_cfg = dict(
        NWNX_SQL_DATABASE = "nwn",
        NWNX_SQL_PASSWORD = "SERVER_USER_PASSWORD",
        NWNX_SQL_USERNAME = "nwn",
        NWNX_SQL_HOST = "172.17.0.1",
        NWNX_SQL_PORT = "3306",
        NWNX_SQL_TYPE = "MYSQL",   
    )


class DevelopmentConfig(Config):
    """Development config."""
    nwnx_sql_cfg = dict(
        NWNX_SQL_DATABASE = "nwn",
        NWNX_SQL_PASSWORD = "SERVER_USER_PASSWORD",
        NWNX_SQL_USERNAME = "nwn",
        NWNX_SQL_HOST = "172.17.0.1",
        NWNX_SQL_PORT = "3306",
        NWNX_SQL_TYPE = "MYSQL"
    )

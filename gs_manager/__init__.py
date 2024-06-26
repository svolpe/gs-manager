import os

from flask import Flask
from .extensions import db, migrate
from .models.users import User
from .models.blog import Post
from .models.server_conf import Config
from flask_sqlalchemy import SQLAlchemy


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/gsmanager.sqlite'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # This key is required to enable a session

#    SQLALCHEMY_BINDS = {
#        "server": "sqlite:///../instance/gsmanager_server.sqlite",
#        },
#    }
    app.config.from_mapping(
        SECRET_KEY = 'dev',
    )
    db.init_app(app)
    migrate.init_app(app, db)
    with app.app_context():
        db.create_all()

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    @app.route('/routes')
    def list_routes():

        #routes_list = app.url_map.iter_rules()

        routes_list = app.url_map
        return routes_list

    from .routes import auth
    app.register_blueprint(auth.bp)

    from .routes import blog
    app.register_blueprint(blog.bp)

    from .routes import server_config
    app.register_blueprint(server_config.sc)

    '''
    app.add_url_rule() associates the endpoint name 'index' with the / url 
    so that url_for('index') or url_for('blog.index') will both work, 
    generating the same / URL either way.
    '''
    app.add_url_rule('/', endpoint='index')

    return app

#if __name__ == '__main__':
#    app = create_app()
#    app.run(debug=True, port=5001)


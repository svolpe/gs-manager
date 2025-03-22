import os

from flask import Flask
from .extensions import db, migrate
from .models.users import User
from .models.blog import Post
from .models.server_nwn import (ServerConfigs, ServerCmds, PcActiveLog, VolumesInfo, VolumesDirs, ServerVolumes,
                                ServerStatus)
from flask import Flask, render_template
from flask_socketio import SocketIO
from flask_session import Session
from flask_login import LoginManager, current_user
from gevent import monkey 

monkey.patch_socket()
monkey.patch_all()


login_manager = LoginManager()
login_manager.login_view = "auth.login"

socketio = SocketIO()
session = Session()

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    config_type = os.getenv('CONFIG_TYPE', default='gs_manager.config.DevelopmentConfig')
    app.config.from_object(config_type)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.filter(User.id == int(user_id)).first()

    # Session type must be set for session.init_app() to work
    # app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_TYPE"] = "filesystem"
    session.init_app(app)
    #Initialize socketio
    socketio.init_app(app, manage_session=False, 
                    cors_allowed_origins=app.config["CORS_ALLOWED_ORIGINS"], 
                    async_mode='gevent')

    # load the instance config, if it exists, when not testing
    # TODO: Look into if this is the correct way to load a config file
    
    #app.config.from_object("gs_manager.config.DevelopmentConfig")

    db.init_app(app)
    migrate.init_app(app, db)
    with app.app_context():
        db.create_all()

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from .routes import auth
    app.register_blueprint(auth.bp)

    from .routes import blog
    app.register_blueprint(blog.bp)

    from .routes import server_config
    app.register_blueprint(server_config.sc)

    from .routes import players
    app.register_blueprint(players.pc)

    from .routes import player_history
    app.register_blueprint(player_history.ph)

    # Ported to using a class
    from .routes.file_manager import FileManagerBp
    file_manager = FileManagerBp(path_storage=app.config['GS_PATH_STORAGE'])
    app.register_blueprint(file_manager.fm)

    # Ported to using a class
    from .routes.volume_manager import VolumeManagerBp
    volume_manager = VolumeManagerBp(path_storage= app.config['GS_PATH_STORAGE'])
    app.register_blueprint(volume_manager.vm)

    '''
    app.add_url_rule() associates the endpoint name 'index' with the / url 
    so that url_for('index') or url_for('blog.index') will both work, 
    generating the same / URL either way.
    '''
    app.add_url_rule('/', endpoint='index')

    return app

if __name__ == "__main__":
    app = create_app()
    socketio.run(app)        


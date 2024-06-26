from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g
)
from werkzeug.exceptions import abort

from ..routes.auth import login_required
from sqlalchemy import (delete, insert)
from ..extensions import db
from ..models.server_nwn import Config, ServerCmds


sc = Blueprint('server_config', __name__)

"""The best way to move forward (for now) is to have a route that will start all active backends and one to 
    list all active members. There should also be a background job tht 
"""

@sc.route('/')
def index():
    query = db.session.query(
        Config.server_name, Config.port, Config.id, Config.module_name)

    return render_template(
        'server_config/index.html', posts=query, server_status='running')


    # return render_template('blog/index.html', posts=query)


@sc.route('/create', methods=('GET', 'POST'))
def create():

    # server_cfg = Config()
    error = None

    if request.method == 'POST':
        server_cfg = request.form.to_dict()
        if not server_cfg['server_name']:
            error = 'server name is required.'

        if error is not None:
            flash(error)
        else:
            # Bulk create of server config settings
            post = Config(**server_cfg)
            db.session.add(post)
            db.session.commit()
            return redirect(url_for('index'))

    return render_template('server_config/create.html')


@sc.route('/<int:id>/server_config', methods=['GET', 'POST'])
def update(id):

    server_cfg = Config.query.filter_by(id=id).first()

    if server_cfg is None:
        abort(404, "Post id {0} doesn't exist.".format(id))

    error = None
    if request.method == 'POST':
        server_cfg = request.form.to_dict()
        if not server_cfg['server_name']:
            error = 'server name is required.'

        if error is not None:
            flash(error)
        else:
            Config.query.filter_by(id=id).update(server_cfg)
            db.session.commit()
            return redirect(url_for('server_config.index'))

    return render_template('server_config/update.html', server_cfg=server_cfg)


@sc.route('/<int:id>/stop', methods=['GET', 'POST'])
def stop(id):
    cmd = ServerCmds(cmd='stop', user_id=g.user.id, cmd_args=str(id))
    db.session.add(cmd)
    db.session.commit()
    return redirect(url_for('server_config.index'))


@sc.route('/<int:id>/start', methods=['GET', 'POST'])
def start(id):
    cmd = ServerCmds(cmd='start', user_id=g.user.id, cmd_args=str(id))
    db.session.add(cmd)
    db.session.commit()
    return redirect(url_for('server_config.index'))
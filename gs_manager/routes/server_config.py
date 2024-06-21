from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, current_app
)
from werkzeug.exceptions import abort

from ..routes.auth import login_required
from sqlalchemy import (delete, insert)
from ..extensions import db
from ..models.server_conf import Config


sc = Blueprint('server_config', __name__)


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




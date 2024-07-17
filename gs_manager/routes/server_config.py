from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g
)
from werkzeug.exceptions import abort

from ..routes.auth import login_required
from sqlalchemy import (delete, insert)
from ..extensions import db
from ..models.server_nwn import ServerConfigs, ServerCmds, VolumesInfo

from flask_wtf import FlaskForm
from flask_wtf import FlaskForm
from wtforms import StringField, FieldList, DecimalField, SelectField, RadioField, IntegerField, SelectMultipleField
from wtforms.validators import InputRequired, NumberRange

sc = Blueprint('server_config', __name__)

"""The best way to move forward (for now) is to have a route that will start all active backends and one to 
    list all active members. There should also be a background job tht 
"""


class ServerConfiguration(FlaskForm):
    server_name = StringField("Server Name", validators=[InputRequired()])
    max_players = IntegerField("Max Players", validators=[NumberRange(min=1, max=100)])
    min_level = IntegerField("Min Level", validators=[NumberRange(min=1, max=60)])
    max_level = IntegerField("Max Level", validators=[NumberRange(min=1, max=60)])
    max_level = IntegerField("Max Level", validators=[NumberRange(min=1, max=60)])
    pause_play = SelectField("Pause And Play", choices=[(0, 'Game only can be paused by DM'),
                                                        (1, 'Game can be paused by players')])
    pvp = SelectField("PVP", choices=[(0, 'None'), (1, 'Party'), (2, 'Full')])
    server_vault = SelectField("Server Vault", choices=[(0, 'Local Characters Only'), (1, 'Server Characters Only')])
    enforce_legal_char = RadioField('Enforce Legal Characters', choices=[(1, 'Yes'), (0, 'No')])
    item_lv_restrictions = RadioField('Item Level Restrictions', choices=[(1, 'Yes'), (0, 'No')])
    game_type = SelectField("Game Type", choices=[(0, 'Action'), (1, 'Story'), (2, 'Story Lite'), (3, 'Role Play'),
                                                  (4, 'Team'), (5, 'Melee'), (6, 'Arena'), (7, 'Social'),
                                                  (8, 'Alternative'), (9, 'PW Action'), (10, 'PW Story'), (11, 'Solo'),
                                                  (12, 'Tech Support')])
    one_party = SelectField("One Party", choices=[(0, 'Allow multiple parties'), (1, 'Only allow one party')])
    difficulty = SelectField("Difficulty", choices=[(1, 'Easy'), (2, 'Normal'), (3, 'D&D Hardcore'),
                                                    (4, 'Very Difficult')])
    auto_save_interval = IntegerField("Auto Save Interval", validators=[InputRequired()])
    player_pwd = StringField("Player Password")
    dm_pwd = StringField("DM Password")
    admin_pwd = StringField("Admin Password")
    module_name = SelectField("Select a Module")
    port = IntegerField("Port (5121)", validators=[NumberRange(min=5120, max=5170)])
    public_server = SelectField("Public Server", choices=[(0, 'Not Public'), (1, 'Public')])
    reload_when_empty = RadioField('Reload When Empty', choices=[(1, 'Yes'), (0, 'No')])
    volumes = SelectMultipleField()
    is_active = RadioField('Server Activate?', choices=[(1, 'Yes'), (0, 'No')])


@sc.route('/')
def index():
    query = db.session.query(
        ServerConfigs.server_name, ServerConfigs.port, ServerConfigs.id, ServerConfigs.module_name)

    return render_template(
        'server_config/index.html', posts=query, server_status='running')


@sc.route('/create', methods=('GET', 'POST'))
def create():
    form = ServerConfiguration()
    pack_info = db.session.query(VolumesInfo.id, VolumesInfo.name).all()
    form.packs.choices = pack_info[0]

    error = None

    if request.method == 'POST':
        server_cfg = request.form.to_dict()
        if not server_cfg['server_name']:
            error = 'server name is required.'

        if error is not None:
            flash(error)
        else:
            # Bulk create of server config settings
            post = ServerConfigs(**server_cfg)
            db.session.add(post)
            db.session.commit()
            return redirect(url_for('index'))
    return render_template('server_config/wtf_create.html', form=form)


@sc.route('/<int:id>/server_config', methods=['GET', 'POST'])
def update(id):
    server_cfg = ServerConfigs.query.filter_by(id=id).first()
    form = ServerConfiguration(data=server_cfg.__dict__)

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
            ServerConfigs.query.filter_by(id=id).update(server_cfg)
            db.session.commit()
            return redirect(url_for('server_config.index'))

    return render_template('server_config/wtf_create.html', form=form)


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

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g
)
from werkzeug.exceptions import abort

from ..routes.auth import login_required
from sqlalchemy import (delete, insert)
from ..extensions import db
from ..models.server_nwn import ServerConfigs, ServerCmds, VolumesInfo, ServerVolumes, VolumesDirs

from flask_wtf import FlaskForm
from flask_wtf import FlaskForm
from wtforms import StringField, FieldList, SelectField, RadioField, IntegerField, SelectMultipleField, FormField
from wtforms.validators import InputRequired, NumberRange

import os

sc = Blueprint('server_config', __name__)

"""The best way to move forward (for now) is to have a route that will start all active backends and one to 
    list all active members. There should also be a background job tht 
"""


class ServerConfiguration(FlaskForm):
    server_name = StringField("Server Name", validators=[InputRequired()])
    max_players = IntegerField("Max Players", validators=[NumberRange(min=1, max=100), InputRequired()])
    min_level = IntegerField("Min Level", validators=[NumberRange(min=1, max=40), InputRequired()])
    max_level = IntegerField("Max Level", validators=[NumberRange(min=1, max=40), InputRequired()])
    pause_play = SelectField("Pause And Play", choices=[(0, 'Game only can be paused by DM'),
                                                        (1, 'Game can be paused by players')],
                             validators=[InputRequired()])
    pvp = SelectField("PVP", choices=[(0, 'None'), (1, 'Party'), (2, 'Full')], validators=[InputRequired()])
    server_vault = SelectField("Server Vault", choices=[(0, 'Local Characters Only'), (1, 'Server Characters Only')],
                               validators=[InputRequired()])
    enforce_legal_char = RadioField('Enforce Legal Characters', choices=[(1, 'Yes'), (0, 'No'), ],
                                    validators=[InputRequired()])
    item_lv_restrictions = RadioField('Item Level Restrictions', choices=[(1, 'Yes'), (0, 'No')],
                                      validators=[InputRequired()])
    game_type = SelectField("Game Type", choices=[(0, 'Action'), (1, 'Story'), (2, 'Story Lite'), (3, 'Role Play'),
                                                  (4, 'Team'), (5, 'Melee'), (6, 'Arena'), (7, 'Social'),
                                                  (8, 'Alternative'), (9, 'PW Action'), (10, 'PW Story'), (11, 'Solo'),
                                                  (12, 'Tech Support')], validators=[InputRequired()])
    one_party = SelectField("One Party", choices=[(0, 'Allow multiple parties'), (1, 'Only allow one party')],
                            validators=[InputRequired()])
    difficulty = SelectField("Difficulty", choices=[(1, 'Easy'), (2, 'Normal'), (3, 'D&D Hardcore'),
                                                    (4, 'Very Difficult')], validators=[InputRequired()])
    auto_save_interval = IntegerField("Auto Save Interval", validators=[InputRequired()])
    player_pwd = StringField("Player Password")
    dm_pwd = StringField("DM Password")
    admin_pwd = StringField("Admin Password")
    module_name = SelectField("Select a Module", choices=[("DockerDemo", "DockerDemo"), ], validators=[InputRequired()])
    port = IntegerField("Port (5121)", validators=[NumberRange(min=5120, max=5170), InputRequired()])
    public_server = SelectField("Public Server", choices=[(0, 'Not Public'), (1, 'Public')],
                                validators=[InputRequired()])
    reload_when_empty = RadioField('Reload When Empty', choices=[(1, 'Yes'), (0, 'No')], validators=[InputRequired()])
    volumes = SelectMultipleField()
    database = RadioField('Use SQL Database?', choices=[('yes', 'Yes'), ('no', 'No')], validators=[InputRequired()])
    is_active = RadioField('Server Activate?', choices=[(1, 'Yes'), (0, 'No')], validators=[InputRequired()])


class ServerConfigDynamic(FlaskForm):
    configuration = FieldList(FormField(ServerConfiguration), min_entries=0)


@sc.route('/')
def index():
    query = db.session.query(
        ServerConfigs.server_name, ServerConfigs.port, ServerConfigs.id, ServerConfigs.module_name)

    return render_template(
        'server_config/index.html', posts=query, server_status='running')


@sc.route('/create', methods=('GET', 'POST'))
def create():
    form = ServerConfiguration()

    volumes = db.session.query(VolumesInfo.id, VolumesInfo.name).all()

    volume_list = []
    for volume in volumes:
        volume_list.append(tuple(volume))

    form.volumes.choices = volume_list

    error = None

    if request.method == 'POST':
        server_cfg = request.form.to_dict()
        del server_cfg["volumes"]
        if not server_cfg['server_name']:
            error = 'server name is required.'

        if error is not None:
            flash(error)
        else:
            # Bulk create of server config settings
            post = ServerConfigs(**server_cfg)
            db.session.add(post)
            db.session.commit()

            # Add New Volumes if there are any
            server_cfg_vols = request.form.to_dict(flat=False)
            if 'volumes' in server_cfg_vols:
                volumes_info_id = server_cfg_vols['volumes']
                for vol_info_id in volumes_info_id:
                    row = ServerVolumes(server_configs_id=post.id, volumes_info_id=vol_info_id)
                    db.session.add(row)
                db.session.commit()

            return redirect(url_for('index'))
    return render_template('server_config/wtf_create.html', form=form)


# TODO: This route needs to be refactored, it has gotten quite big and using the dict for db might not be the best idea.
@sc.route('/<int:id>/server_config', methods=['GET', 'POST'])
def update(id):
    server_cfg = ServerConfigs.query.filter_by(id=id).first()

    if server_cfg is None:
        abort(404, "Post id {0} doesn't exist.".format(id))

    form = ServerConfiguration()

    # Load values for volume list
    volumes = db.session.query(VolumesInfo.id, VolumesInfo.name).all()
    volume_list = []
    for volume in volumes:
        volume_list.append(tuple(volume))

    form.volumes.choices = volume_list  # [pack_info]

    # Set previously selected choices as default for volume list and volumes directories
    volume_list = []
    volumes = ServerVolumes.query.filter_by(server_configs_id=id).all()
    for volume in volumes:
        volume_list.append(volume.volumes_info_id)
    form.volumes.default = volume_list

    # Get the list of modules based on mounted volume directory
    modules_dir = ((db.session.query(VolumesInfo.name, VolumesInfo.description,
                                 VolumesDirs.dir_src_loc, VolumesDirs.dir_mount_loc
                                 ).join(VolumesInfo, ServerVolumes.volumes_info_id == VolumesInfo.id
                                        ).join(ServerVolumes, VolumesDirs.volumes_info_id == VolumesInfo.id)
                ).filter(ServerVolumes.server_configs_id == id
                         ).filter(VolumesDirs.dir_mount_loc == '/nwn/home/modules')).first()

    # Check if there is a module directory
    if modules_dir:
        # TODO: Find a better way to do this since this approach uses a private object
        dir = modules_dir._mapping['dir_src_loc']
        server_modules = []
        for file in os.listdir(dir):
            # check only text files
            if file.endswith('.mod'):
                mod_name = os.path.splitext(file)[0]
                server_modules.append(tuple([mod_name,mod_name]))
        form.module_name.choices = server_modules

    form.module_name.default = server_cfg.module_name

    # Process form, this needs to be done after all defaults are set and it needs to be passed the data.
    form.process(data=server_cfg.__dict__)
    error = None
    if request.method == 'POST':
        # Delete old volumes
        ServerVolumes.query.filter(ServerVolumes.server_configs_id == id).delete()
        db.session.commit()

        # Add New Volumes if there are any
        server_cfg_vols = request.form.to_dict(flat=False)
        if 'volumes' in server_cfg_vols:
            volumes_info_id = server_cfg_vols['volumes']
            for vol_info_id in volumes_info_id:
                row = ServerVolumes(server_configs_id=id, volumes_info_id=vol_info_id)
                db.session.add(row)
            db.session.commit()
        # Get flat dict so it can be directly passed to the update
        server_cfg = request.form.to_dict(flat=True)

        if not server_cfg['server_name']:
            error = 'server name is required.'

        if error is not None:
            flash(error)
        else:
            # Remove volumes from the dict since its not part of the db
            # TODO: Fix how volumes are handled by the server_cfg so there is no need to manually delete
            if 'volumes' in server_cfg:
                del server_cfg["volumes"]

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

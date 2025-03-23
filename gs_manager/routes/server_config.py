from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g
)
from werkzeug.exceptions import abort

from ..routes.auth import login_required
from sqlalchemy import (delete, insert)
from ..extensions import db, clone_model
from ..models.server_nwn import (ServerConfigs, ServerCmds, VolumesInfo, ServerVolumes, VolumesDirs,
                                ServerStatus, SystemWatchdog)

from .server_config_forms import ServerConfiguration, ServerConfigDynamic

import os, datetime
from .. import socketio
import subprocess
from flask_socketio import emit
from flask import request

sc = Blueprint('server_config', __name__)

"""The best way to move forward (for now) is to have a route that will start all active backends and one to 
    list all active members. There should also be a background job tht 
"""

def cfg_delete(id):
    # Delete the server config
    ServerConfigs.query.filter_by(id=id).delete()

    # Delete all volumes associated with it
    ServerVolumes.query.filter_by(server_configs_id=id).delete()
    db.session.commit()
def cfg_copy(id):
    # Clone server config
    config_cp = ServerConfigs.query.filter_by(id=id)
    config_cp_obj = config_cp.all()[0]
    row_new = clone_model(config_cp_obj, server_name=config_cp_obj.server_name + "_copy", is_active=0)

    # Clone server volumes
    vol_cp = ServerVolumes.query.filter_by(server_configs_id=id).all()
    for vol in vol_cp:
        clone_model(vol, server_configs_id=row_new.id)

#Check if server is still up and running
def is_server_ok():
    ''''Checks if the backend server is updating the heartbeat'''  
    heartbeat = SystemWatchdog.query.filter_by(component="backend_nwn").first()
    cur_datetime = datetime.datetime.now()
    if not heartbeat or (cur_datetime - heartbeat.heart_beat).seconds > 60:
        return False
    else:
        return True

def get_server_diffs(cfgs1, cfgs2):
    cfgs1_keys = set(cfgs1.keys())
    cfgs2_keys = set(cfgs2.keys())
    common_keys = list(cfgs1_keys & cfgs2_keys)
    diff = {}
    
    for key in common_keys:
        if cfgs1[key] != cfgs2[key]:
            diff[key] = {"dict1": cfgs1[key], "dict2": cfgs2[key]}
    rkeys = list(cfgs1_keys - cfgs2_keys)
    akeys = list(cfgs2_keys - cfgs1_keys)
    
    removed={}
    added={}
    for key in rkeys:
        removed[key] = cfgs1[key]
    for key in akeys:
        added[key] = cfgs2[key]

    changed = diff
    
    if (removed or added or changed) == {}:
        return {}
    else:
        return {
            "removed": removed,
            "added": added,
            "changed": diff
        }
        
def get_server_info():
    query = ServerConfigs.query.join(ServerStatus, ServerStatus.server_cfg_id == ServerConfigs.id, isouter=True) \
                        .with_entities(ServerConfigs.server_name, ServerConfigs.port, ServerConfigs.id, ServerConfigs.module_name, ServerStatus.status,
        ServerConfigs.is_active).all()

    status = {}
    update = {}
    for q in query:
        if not is_server_ok():
            update = {'severity':'error', 'status':'server down', 'action':'none'}
        elif q.status == None:
            update={'severity':'none', 'status':'not activated', 'action':'start'}
        elif q.status == "running":
            update={'severity':'good', 'status':q.status, 'action':'stop'}
        elif q.status in "starting stopping loading running":
            update={'severity':'warn', 'status':q.status, 'action':'none'}
        elif q.status == "stopped":
            if q.is_active:
                update={'severity':'error', 'status':q.status, 'action':'start'}
            else:
                update={'severity':'none', 'status':'not activated', 'action':'start'}   
        else:
            update={'severity':'error', 'status':q.status, 'action':'start'}
        
        status[q.id] = q._asdict()
        status[q.id].update(update)
    return status  

@sc.route('/')
def index():
    '''TODO: replace the query with:
        query = ServerConfigs.query.join(ServerStatus, ServerStatus.server_cfg_id == ServerConfigs.id).with_entities(ServerConfigs.server_name, ServerConfigs.port, ServerConfigs.id, ServerConfigs.module_name, ServerStatus.status,ServerConfigs.is_active).all()
    '''
    query = db.session.query(
        ServerConfigs.server_name, ServerConfigs.port, ServerConfigs.id, ServerConfigs.module_name, ServerStatus.status,
        ServerConfigs.is_active
    ).join(ServerStatus, ServerStatus.server_cfg_id == ServerConfigs.id, isouter=True)
    
    if is_server_ok():
        server_status="up"
    else:
        server_status="down"

    return render_template(
        'server_config/index.html', posts=query, server_status=server_status)
@sc.route('/cfg_data')
def cfg_data():
    statuses = get_server_info()
    rows = []
    for cfg in statuses.values():
        rows.append({
            'id':cfg['id'],
            'server': cfg['server_name'],
            'port': cfg['port'],
            'module': cfg['module_name'],
            'severity': statuses[cfg['id']]['severity'],
            'status':  statuses[cfg['id']]['status'],
            'action':  statuses[cfg['id']]['action']
        })
    data = {'data': rows}
    return data

@socketio.on('connect', namespace='/server_cfgs')
def handle_connect():
    print('Client connected')

@socketio.on("do_action", namespace='/server_cfgs')
def do_action(action):
    cmd = list(action.keys())[0]
    id = action[cmd]["id"]
    cmd = cmd.lower()
    if cmd == "delete":
        cfg_delete(id)
    elif cmd == "copy":
        cfg_copy(id)
    elif cmd == "stop" or cmd == "start":
        #TODO: figure out how to handle the userID instead of just using 0
        send_cmd(cmd, 0, str(id))


@socketio.on("get_statuses", namespace='/server_cfgs')
def get_statuses():
    old_stats = get_server_info()

    # Send the current status to the client
    sid = request.sid
    emit('status_changed', {'data': old_stats}, room=sid)
    while True:
        cur_stats = get_server_info()
        if cur_stats != old_stats:
            sid = request.sid
            emit('status_changed', {'data': cur_stats}, room=sid)
            old_stats = cur_stats

        socketio.sleep(1)

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
        if "volumes" in server_cfg:
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


def send_cmd(cmd, user_id, cmd_args):

    # Check if the same command is already queued
    cmd_exist = (ServerCmds.query.filter_by(cmd=cmd).
                filter_by(cmd_args=cmd_args).
                filter_by(cmd_executed_time=None).first())

    # If command is not already queued then send it, otherwise don't!
    if not cmd_exist:
        cmd = ServerCmds(cmd=cmd, user_id=user_id, cmd_args=cmd_args)
        db.session.add(cmd)
        db.session.commit()
    return redirect(url_for('server_config.index'))


@sc.route('/<int:id>/delete', methods=['GET', 'POST'])
def delete(id):
    """This route deletes a server config from the db"""

    cfg_delete(id)
    return redirect(url_for('server_config.index'))


@sc.route('/<int:id>/copy', methods=['GET', 'POST'])
def copy(id):
    """This route copies an existing server config and adds _copy to the end of the name"""

    cfg_copy(id)

    return redirect(url_for('server_config.index'))


@sc.route('/<int:id>/stop', methods=['GET', 'POST'])
def stop(id):
    send_cmd('stop', g.user.id, str(id))
    return redirect(url_for('server_config.index'))


@sc.route('/<int:id>/start', methods=['GET', 'POST'])
def start(id):
    cmd = ServerCmds(cmd='start', user_id=g.user.id, cmd_args=str(id))
    send_cmd('start', g.user.id, str(id))
    return redirect(url_for('server_config.index'))

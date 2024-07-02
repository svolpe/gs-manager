from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g
)
from werkzeug.exceptions import abort

from ..routes.auth import login_required
from sqlalchemy import (delete, insert)
from ..extensions import db
from ..models.server_nwn import VolumesDirs, VolumesInfo, ServerVolumes
from sqlalchemy import null

vm = Blueprint('volume_manager', __name__)


@vm.route('/volumes', methods=('GET',))
def index():

    volumes = (db.session.query(ServerVolumes.server_configs_id, VolumesInfo.name, VolumesInfo.description,
                                VolumesDirs.dir_src_loc, VolumesDirs.dir_mount_loc, VolumesDirs.id
                                ).join(VolumesInfo, VolumesDirs.volumes_info_id == VolumesInfo.id)).all()

    volumes_sorted = dict()
    row = dict()
    for volume in volumes:
        row = {volume.dir_src_loc: {'mount_loc': volume.dir_mount_loc, 'id': volume.id}}
        if volume.name in volumes_sorted:
            volumes_sorted[volume.name].update(row)
        else:
            volumes_sorted[volume.name] = row
            volumes_sorted[volume.name]['description'] = volume.description
    return render_template('volume_manager/index.html', volumes=volumes_sorted)


@vm.route('/volumes/<int:id>/delete')
def delete(id):
    VolumesDirs.query.filter(VolumesDirs.id == id).delete()
    db.session.commit()
    return redirect(url_for('index'))

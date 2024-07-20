from flask import (
    Blueprint, redirect, render_template, request, url_for, g
)

from ..extensions import db
from ..models.server_nwn import VolumesDirs, VolumesInfo

import os
import shutil

from wtforms import (StringField, FieldList, DecimalField, SelectField, RadioField, IntegerField, BooleanField,
                     FormField, Form, HiddenField, )

from wtforms.validators import InputRequired
from ..extensions import PATH_STORAGE

vm = Blueprint('volume_manager', __name__)


class VolumeGroup(Form):
    name = StringField("Name: ", validators=[InputRequired()])
    description = StringField("Description: ")


class VolumeItem(Form):
    vol_id = HiddenField()
    dir_src_loc = StringField()
    dir_mount_loc = StringField(validators=[InputRequired()])
    read_write = SelectField("Access Permissions", choices=[('ro', 'Read-Only'), ('rw', 'Read/Write')])
    delete = BooleanField('yes')

    def __init__(self, **kwargs):
        """Override the labels for the mount location setting them to the data of the src location"""
        super().__init__(**kwargs)
        self.dir_mount_loc.label = self.dir_src_loc.data

        # TODO: There has a be a better way to corrilate the database data with the form data
        # Add the volume id to the field ID to make it easier to group together
        # This code is basically just over-riding the prefix functionality
        for data in self.data:
            self[data].name = f"{self.vol_id.data}_{data}"


class VolumesForm(Form):
    volume_list = FieldList(FormField(VolumeItem), min_entries=0)


def volumes_form_to_id_dict(volumes):
    volumes_dict = dict()
    for volume in volumes:
        split_data = volume.split('_', 1)
        vol_id = split_data[0]
        field = split_data[1]

        if vol_id in volumes_dict:
            volumes_dict[vol_id].update({field: volumes[volume]})
        else:
            volumes_dict[vol_id] = {field: volumes[volume]}
    return volumes_dict


@vm.route('/volumes')
def index():
    volumes = (db.session.query(VolumesInfo.name, VolumesInfo.description,
                                VolumesDirs.dir_src_loc, VolumesDirs.dir_mount_loc, VolumesDirs.id,
                                VolumesInfo.id.label('volume_info_id')
                                ).join(VolumesDirs, VolumesInfo.id == VolumesDirs.volumes_info_id, isouter=True)).all()

    volumes_sorted = dict()
    row = dict()
    for volume in volumes:
        row = {volume.dir_src_loc: {'mount_loc': volume.dir_mount_loc, 'id': volume.id}}
        if volume.name in volumes_sorted:
            volumes_sorted[volume.name].update(row)
        else:
            volumes_sorted[volume.name] = row
            volumes_sorted[volume.name]['description'] = volume.description
            volumes_sorted[volume.name]['volume_info_id'] = volume.volume_info_id

    return render_template('volume_manager/index.html', volumes=volumes_sorted)


@vm.route('/volumes/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        group = request.form.to_dict()
        vol = VolumesInfo(name=group['name'], description=group['description'])
        db.session.add(vol)
        db.session.commit()
        return redirect(url_for('volume_manager.index'))

    form = VolumeGroup()
    return render_template(f'volume_manager/create.html', form=form, )


@vm.route('/volumes/<int:id>/delete')
def delete(id):
    VolumesDirs.query.filter(VolumesDirs.id == id).delete()
    db.session.commit()
    return redirect(url_for('index'))


@vm.route('/volumes/add')
def add():
    id = request.args.get('id')
    dir = request.args.get('dir')
    volume = VolumesDirs(active=0, volumes_info_id=id, dir_src_loc=dir)
    db.session.add(volume)
    db.session.commit()
    return redirect(url_for('volume_manager.edit', id=id))


@vm.route('/volumes/<int:id>/add_dir')
def add_dir(id):
    pass


@vm.route('/volumes/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    if request.method == 'POST':
        volumes = request.form.to_dict()
        volumes = volumes_form_to_id_dict(volumes)
        # TODO: Figure out how to update all rows and put here. Also add support for read/write
        for volume in volumes:
            if 'delete' in volumes[volume].keys():
                VolumesDirs.query.filter_by(id=volume).delete()
                db.session.commit()
            else:
                row = VolumesDirs.query.filter_by(id=volume).first()
                row.dir_mount_loc = volumes[volume]['dir_mount_loc']
                row.read_write = volumes[volume]['read_write']
                row.active = 1
                db.session.commit()

        return redirect(url_for('volume_manager.index'))

    cwd = os.getcwd()
    shared_prefix = os.path.commonprefix([cwd, PATH_STORAGE])
    if shared_prefix != PATH_STORAGE:
        cwd = PATH_STORAGE
        os.chdir(cwd)
    file_list = os.listdir(cwd)

    volumes = ((db.session.query(VolumesInfo.name, VolumesInfo.description,
                                 VolumesDirs.dir_src_loc, VolumesDirs.dir_mount_loc, VolumesDirs.id,
                                 VolumesDirs.read_write, VolumesInfo.id.label('volume_info_id'),
                                 VolumesDirs.id.label('vol_id'),
                                 ).join(VolumesDirs, VolumesDirs.volumes_info_id == VolumesInfo.id, isouter=True)
                ).filter(VolumesInfo.id == id))

    volume_entry = list()
    for volume in volumes:
        # TODO: This is using an private variable, find a better way to do this
        volume_entry.append(volume._mapping)

    # Check if there are any volume directories associated with the group
    if volume_entry[0]['vol_id'] is not None:
        form = VolumesForm(volume_list=volume_entry)
        submit_en = True
    else:
        submit_en = False
        form = []

    group_name = volumes[0].name

    return render_template(f'volume_manager/edit.html', volumes=volumes, name=group_name,
                           file_list=file_list, form=form, cwd=cwd, id=id, submit_en=submit_en)


@vm.route('/volumes/<int:id>/update')
def update(id):
    VolumesDirs.query.filter(VolumesDirs.id == id).delete()
    db.session.commit()
    return redirect(url_for('index'))


def listdir_no_hidden(path):
    for f in os.listdir(path):
        if not f.startswith('.'):
            return f


def prefix_removal(text, prefixes):
    first_word = text.split()[0]
    if first_word.startswith(prefixes):
        return text[len(prefixes):]
    return text


@vm.route('/volumes/files/upload', methods=['GET', 'POST'])
def uploadb():
    # if request.method == 'POST':
    # return redirect(url_for('server_config.upload'))
    return render_template('file_manager/upload.html', modules=[{'module_name': 'mod1', 'dir_location': 'dir1'},
                                                                {'module_name': 'mod2', 'dir_location': 'dir2'}])


# handle 'cd' command
@vm.route('/volumes/cd')
def cd():
    # run 'level up' command
    path = request.args.get('path')
    id = request.args.get('id')
    abs_path = os.path.abspath(path)
    shared_prefix = os.path.commonprefix([abs_path, PATH_STORAGE])
    # Make sure there is not a request to leave game storage directory
    if shared_prefix == PATH_STORAGE:
        os.chdir(path)

    # redirect to file manager
    return redirect(url_for('volume_manager.edit', id=id))


# handle 'make directory' command
@vm.route('/volumes/md')
def md():
    # create new folder
    cwd = os.getcwd()
    shared_prefix = os.path.commonprefix([cwd, PATH_STORAGE])

    # The following command protects against deleting files outside of the storage.
    if shared_prefix != PATH_STORAGE:
        return 'bad request!', 400
    else:
        os.mkdir(request.args.get('folder'))
        id = request.args.get('id')
        # redirect to file manager
        return redirect(url_for('volume_manager.edit', id=id))


# handle 'make directory' command
@vm.route('/volumes/rm')
def rm():
    cwd = os.getcwd()
    shared_prefix = os.path.commonprefix([cwd, PATH_STORAGE])

    # The following command protects against deleting files outside the storage.
    if shared_prefix != PATH_STORAGE:
        return 'bad request!', 400
    else:
        # remove certain directory
        shutil.rmtree(cwd + '/' + request.args.get('dir'))
        # redirect to file manager
        return redirect('/volumes/')


# view text files
@vm.route('/volumes/view')
def view():
    # get the file content
    with open(request.args.get('file')) as f:
        return f.read().replace('\n', '<br>')


@vm.route('/volumes/<int:id>/rm_mount')
def rm_mount(id):
    pass


'''Notes:
 I think  what makes the most sense is to list the group and volumes that you are editing at the top (form)
 Everytime you click on an add it adds a new volume to the above form and has an empty field to enter the mount point.
 '''

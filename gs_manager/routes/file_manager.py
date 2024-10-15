from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g, render_template_string
)

import os
import subprocess
import shutil
from ..extensions import db, change_dir_safe, PATH_STORAGE

fm = Blueprint('file_manager', __name__)


def listdir_no_hidden(path):
    for f in os.listdir(path):
        if not f.startswith('.'):
            return f


def prefix_removal(text, prefixes):
    first_word = text.split()[0]
    if first_word.startswith(prefixes):
        return text[len(prefixes):]
    return text


@fm.route('/file_manager/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        f = request.files['file']
        cwd = os.getcwd()
        file_path = os.path.join(cwd, f.filename)

        # If the file already exists then delete it first
        if os.path.exists(file_path):
            os.remove(file_path)

        f.save(file_path)
        return redirect('/file_manager')
        # return render_template("file_manager/index.html")



# handle root route
@fm.route('/file_manager')
def index():
    cwd = os.getcwd()
    new_path = request.args.get('path', cwd)
    cwd = change_dir_safe(new_path)
    file_list2 = os.listdir(cwd)
    file_list = subprocess.check_output('ls', shell=True).decode('utf-8').split('\n')  # use 'dir' command on Windows
    return render_template('file_manager/index.html', file_list=file_list2,
                            cwd=cwd, )


# handle 'cd' command
@fm.route('/file_manager/cd')
def cd():
    # run 'level up' command
    cur_dir = os.getcwd()
    new_path = request.args.get('path', cur_dir)
    go_parent = request.args.get('go_par', 'no')
    
    id = request.args.get('id')
    if go_parent == 'yes':
        new_path = os.path.abspath(os.path.join(new_path, os.pardir))

    # redirect to file manager
    return redirect(url_for('file_manager.index', id=id, path=new_path))

# handle 'make directory' command
@fm.route('/file_manager/md')
def md():
    # create new folder
    os.mkdir(request.args.get('folder'))

    # redirect to fole manager
    return redirect('/file_manager')


# handle 'make directory' command
@fm.route('/file_manager/rm')
def rm():
    rm_loc = request.args.get('path')
    cur_loc = []
    shared_prefix = os.path.commonprefix([rm_loc, PATH_STORAGE])

    # The following command protects against deleting files outside of the storage.
    if shared_prefix != PATH_STORAGE:
        return 'bad request!', 400
    else:
        cur_loc = os.path.dirname(rm_loc)
        # remove certain directory
        if os.path.isfile(rm_loc):
            os.remove(rm_loc)
        elif os.path.isdir(rm_loc):
            shutil.rmtree(rm_loc)
        else:
            return 'bad request!', 400
        # redirect to file manager
    return redirect(url_for('file_manager.index', id=id, path=cur_loc))



# view text files
@fm.route('/file_manager/view')
def view():
    # get the file content
    with open(request.args.get('file')) as f:
        return f.read().replace('\n', '<br>')

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g, render_template_string
)

import os
import subprocess
import shutil
from ..extensions import PATH_STORAGE

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
        return render_template("file_manager/upload_success.html", name=f.filename)



# handle root route
@fm.route('/file_manager/')
def root():
    cwd = os.getcwd()
    shared_prefix = os.path.commonprefix([cwd, PATH_STORAGE])
    if shared_prefix != PATH_STORAGE:
        cwd = PATH_STORAGE
        os.chdir(cwd)
    file_list2 = os.listdir(cwd)
    file_list = subprocess.check_output('ls', shell=True).decode('utf-8').split('\n')  # use 'dir' command on Windows
    return render_template('file_manager/index.html', file_list=file_list2,
                           cwd=cwd, )


# handle 'cd' command
@fm.route('/file_manager/cd')
def cd():
    # run 'level up' command
    path = request.args.get('path')
    abs_path = os.path.abspath(path)
    shared_prefix = os.path.commonprefix([abs_path, PATH_STORAGE])
    # Make sure there is not a request to leave game storage directory
    if shared_prefix == PATH_STORAGE:
        os.chdir(path)

    # redirect to file manager
    return redirect('/file_manager/')


# handle 'make directory' command
@fm.route('/file_manager/md')
def md():
    # create new folder
    os.mkdir(request.args.get('folder'))

    # redirect to fole manager
    return redirect('/file_manager/')


# handle 'make directory' command
@fm.route('/file_manager/rm')
def rm():
    cwd = os.getcwd()
    shared_prefix = os.path.commonprefix([cwd, PATH_STORAGE])

    # The following command protects against deleting files outside of the storage.
    if shared_prefix != PATH_STORAGE:
        return 'bad request!', 400
    else:
        # remove certain directory
        shutil.rmtree(cwd + '/' + request.args.get('dir'))
        # redirect to file manager
        return redirect('/file_manager/')


# view text files
@fm.route('/file_manager/view')
def view():
    # get the file content
    with open(request.args.get('file')) as f:
        return f.read().replace('\n', '<br>')

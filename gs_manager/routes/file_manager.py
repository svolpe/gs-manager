from flask import (
    Blueprint, flash, send_file, redirect, render_template, request, url_for, g, render_template_string
)

import os
import subprocess
import shutil
from ..extensions import db, change_dir_safe
import shutil


class FileManagerBp(object):
    
    def __init__(self, path_storage):
        self.path_storage = path_storage
        self.fm = self.create_bp()
    
    def create_bp(self):
        fm = Blueprint('file_manager', __name__)
        def listdir_no_hidden(self, path):
            for f in os.listdir(path):
                if not f.startswith('.'):
                    return f

        def prefix_removal(self, text, prefixes):
            first_word = text.split()[0]
            if first_word.startswith(prefixes):
                return text[len(prefixes):]
            return text

        @fm.route('/file_manager/download')
        def download():
            path = request.args.get('path')
            return send_file(path, as_attachment=True)


        @fm.route('/file_manager/upload', methods=['GET', 'POST'])
        def upload():
            if request.method == 'POST':
                
                fname = request.files['file']

                if fname.filename == '':
                    return render_template('file_manager/no_file.html')
                
                cwd = request.form.get('cwd', "/dev/null")
                
                shared_prefix = os.path.commonprefix([cwd, self.path_storage])

                # The following command protects against deleting files outside of the storage.
                if shared_prefix != self.path_storage:
                    cwd = self.path_storage

                file_path = os.path.join(cwd, fname.filename)

                # If the file already exists then delete it first
                if os.path.exists(file_path):
                    os.remove(file_path)

                fname.save(file_path)
                return redirect(url_for('file_manager.index', path=cwd))
                # return render_template("file_manager/index.html")

        # handle root route
        @fm.route('/file_manager')
        def index():
            cwd = os.getcwd()
            new_path = request.args.get('path', cwd)
            cwd = change_dir_safe(new_path, self.path_storage)
            file_list = os.scandir(cwd)
            file_info = []
            for file in file_list:
                if file.is_dir():
                    file_info.append([file.name, 'dir'])
                elif file.is_file():
                    file_info.append([file.name, 'file'])
                else:
                    continue
            return render_template('file_manager/index.html', file_info=file_info,
                                    cwd=cwd, )


        # handle 'cd' command
        @fm.route('/file_manager/cd')
        def cd():
            # run 'level up' command
            cur_dir = os.getcwd()
            new_path = request.args.get('path', cur_dir)
            go_parent = request.args.get('go_par', 'no')
            
            if go_parent == 'yes':
                new_path = os.path.abspath(os.path.join(new_path, os.pardir))

            # redirect to file manager
            return redirect(url_for('file_manager.index', path=new_path))

        # handle 'make directory' command
        @fm.route('/file_manager/md')
        def md():
            # create new folder
            os.mkdir(request.args.get('folder'))

            # redirect to file manager
            return redirect('/file_manager')


        # handle 'make directory' command
        @fm.route('/file_manager/rm')            
        def rm():
            rm_loc = request.args.get('path')
            cur_loc = []
            shared_prefix = os.path.commonprefix([rm_loc, self.path_storage])

            # The following command protects against deleting files outside of the storage.
            if shared_prefix != self.path_storage:
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
            
        # Return the Blueprint FM to be used by the flask app
        return fm
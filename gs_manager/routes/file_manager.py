from flask import (
    Blueprint, flash, send_file, redirect, render_template, request, url_for, g, render_template_string
)

import os
import subprocess
import shutil
from ..extensions import db, change_dir_safe
import shutil
from ..models.server_nwn import PcActiveLog
from ..tools.nwn_editors.character_editor import Character

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
            return text[len(prefixes):] if first_word.startswith(prefixes) else text

        @fm.route('/file_manager/download')
        def download():
            path = request.args.get('path')
            return send_file(path, as_attachment=True)


        @fm.route('/file_manager/upload', methods=['GET', 'POST'])
        def upload():
            if request.method != 'POST':
                return
            
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

        # handle root route
        @fm.route('/file_manager')
        def index():
            cwd = os.getcwd()
            new_path = request.args.get('path', cwd)
            cwd = change_dir_safe(new_path, self.path_storage)
            file_list = os.scandir(cwd)
            file_info = []
            cd_keys = {r.cd_key:r.player_name for r in db.session.query(PcActiveLog.cd_key, PcActiveLog.player_name).distinct()}
            for file in file_list:
                file_name = os.path.split(file)[1]
                file_string = cd_keys[file_name] if file_name in cd_keys else file_name

                if file.is_dir():
                    # TODO Add test to see if the dir name is in the database of users logged in then add tag to display as the fname
                    file_info.append([file.name, 'dir', file_string])
                elif file.is_file():

                    if os.path.splitext(file)[1] == '.bic':
                        file_info.append([file.name, 'bic', file_string])
                    else:
                        file_info.append([file.name, 'file', file_string])

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

            if shared_prefix != self.path_storage:
                return 'bad request!', 400
            cur_loc = os.path.dirname(rm_loc)
            # remove certain directory
            if os.path.isfile(rm_loc):
                os.remove(rm_loc)
            elif os.path.isdir(rm_loc):
                shutil.rmtree(rm_loc)
            else:
                return 'bad request!', 400
            return redirect(url_for('file_manager.index', id=id, path=cur_loc))



        # view text files
        @fm.route('/file_manager/view')
        def view():
            # get the file content
            with open(request.args.get('file')) as f:
                return f.read().replace('\n', '<br>')


        @fm.route('/file_manager/edit', methods=('GET', 'POST'))
        def edit():
            
            file = request.args.get('path')
            my_char = Character()
            my_char.load_file(file)
            description = my_char._read_data_moneo('Description') 
            # Not all characters have last names so lets check first
            if "LastName" in my_char.npc_data:
                last_name = my_char.npc_data['LastName'].value,
            else:
                last_name = ""
                
            if request.method == 'POST':
                state = request.form.get('state', '')
                file_name = request.form.get('file_name', '')
                cur_loc = os.path.dirname(file_name)
                shared_prefix = os.path.commonprefix([cur_loc, self.path_storage])
                if shared_prefix != self.path_storage:
                    return 'bad request!', 400

                if state == "update_char":
                    first_name_p = request.form.get('first_name', '')
                    last_name_p = request.form.get('last_name', '')
                    description_p = request.form.get('description', '')
                    my_char._save_data('Firstname', first_name_p)
                    my_char._save_data('Lastname', last_name_p)
                    my_char._save_data('Description', description_p)


                
                return redirect(url_for('file_manager.index', path=cur_loc))

            
            char_data  = dict(
                            portrait = f"portraits/{my_char.npc_data['Portrait'].value}.jpg",
                            first_name = my_char.npc_data['FirstName'].value,
                            last_name = last_name,
                            alignment = my_char.get_alignment(),
                            gender = my_char.npc_data['Gender'].value,
                            deity = my_char.npc_data['Deity'].value,
                            age = my_char.npc_data['Age'].value,
                            race = my_char.npc_data['Race'].value,
                            c_class = my_char.npc_data['Class'].value,
                            gold = my_char.npc_data['Gold'].value,
                            hp = f"{my_char.npc_data['HitPoints'].value} / {my_char.npc_data['MaxHitPoints'].value}",
                            exp = my_char.npc_data['Experience'].value,
                            str = my_char.npc_data['Str'].value,
                            dex = my_char.npc_data['Dex'].value,
                            int = my_char.npc_data['Int'].value,
                            wis = my_char.npc_data['Wis'].value,
                            con = my_char.npc_data['Con'].value,
                            cha = my_char.npc_data['Cha'].value,
                            description = description,
                            subrace = my_char.npc_data['Age'].value,
                            )

            # get the file content
            return render_template('file_manager/edit.html', char_data=char_data,
                                file_name=file, )
        
        # Return the Blueprint FM to be used by the flask app
        return fm
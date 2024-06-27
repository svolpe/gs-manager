from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g
)


fm = Blueprint('file_manager', __name__)


@fm.route('/files/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':4
    # return redirect(url_for('server_config.upload'))
    return render_template('file_manager/upload.html', modules=[{'module_name': 'mod1', 'dir_location': 'dir1'}, {'module_name': 'mod2', 'dir_location': 'dir2'}])

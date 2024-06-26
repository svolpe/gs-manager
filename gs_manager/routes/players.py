from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g
)
from werkzeug.exceptions import abort

from ..routes.auth import login_required
from sqlalchemy import (delete, insert)
from ..extensions import db
from ..models.server_nwn import PcActiveLog
from sqlalchemy import null


pc = Blueprint('players', __name__)

@pc.route('/players')
def index():
    query = (db.session.query(
        PcActiveLog.player_name, PcActiveLog.logon_time, PcActiveLog.docker_name, PcActiveLog.server_name)
             .filter(PcActiveLog.logoff_time.is_(None)))

    return render_template(
        'players/index.html', posts=query)

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g
)
from werkzeug.exceptions import abort

from .auth import login_required
from sqlalchemy import (delete, insert)
from ..extensions import db
from ..models.server_nwn import PcActiveLog
from sqlalchemy import null


ph = Blueprint('player_history', __name__)



@ph.route('/player_history')
def index():     
    return render_template(
        'player_history/index.html')


@ph.route('/player_history/data')
def data():
    query = PcActiveLog.query.filter(PcActiveLog.logoff_time.isnot(None))
    data = {'data': [user.to_dict() for user in query]}
    return data



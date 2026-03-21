from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g
)
from werkzeug.exceptions import abort

from .auth import login_required
from sqlalchemy import delete, insert, func
from ..extensions import db
from ..models.server_nwn import PcActiveLog
from sqlalchemy import null


ph = Blueprint('player_history', __name__)


@ph.route('/player_history')
def index():
    return render_template('player_history/index.html')


@ph.route('/player_history/summary/data')
def summary_data():
    rows = (
        db.session.query(
            PcActiveLog.player_name,
            func.count(PcActiveLog.id).label('login_count'),
            func.max(PcActiveLog.logon_time).label('last_login')
        )
        .filter(PcActiveLog.logoff_time.isnot(None))
        .group_by(PcActiveLog.player_name)
        .all()
    )
    return {'data': [
        {
            'player_name': r.player_name,
            'login_count': r.login_count,
            'last_login': r.last_login,
        }
        for r in rows
    ]}


@ph.route('/player_history/list')
def list_view():
    return render_template('player_history/list.html')


@ph.route('/player_history/data')
def data():
    query = PcActiveLog.query.filter(PcActiveLog.logoff_time.isnot(None))
    return {'data': [user.to_dict() for user in query]}


@ph.route('/player_history/player/<player_name>')
def player_detail(player_name):
    return render_template('player_history/player_detail.html', player_name=player_name)


@ph.route('/player_history/player/<player_name>/data')
def player_data(player_name):
    query = PcActiveLog.query.filter(
        PcActiveLog.logoff_time.isnot(None),
        PcActiveLog.player_name == player_name
    )
    return {'data': [row.to_dict() for row in query]}



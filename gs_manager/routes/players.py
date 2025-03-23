from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g
)
from werkzeug.exceptions import abort

from ..routes.auth import login_required
from sqlalchemy import (delete, insert)
from ..extensions import db
from ..models.server_nwn import PcActiveLog
from sqlalchemy import null
from .. import socketio
from flask_socketio import emit
from flask import request

pc = Blueprint('players', __name__)

def get_active_players():
    query = (PcActiveLog.query.with_entities(
    PcActiveLog.id, PcActiveLog.player_name, PcActiveLog.logon_time, PcActiveLog.docker_name, PcActiveLog.server_name,
    PcActiveLog.character_name)
        .filter(PcActiveLog.logoff_time.is_(None))).all()
    data = []
    for row in query:
        record = row._asdict()
        record['logon_time'] = record['logon_time'].strftime("%Y-%m-%d %H:%M:%S")
        data.append(record)
    return data

@pc.route('/player_data')
def player_data():

    players = get_active_players()
    data = {'data': players}
    
    return data

@pc.route('/players')
def index():
    query = (db.session.query(
        PcActiveLog.player_name, PcActiveLog.logon_time, PcActiveLog.docker_name, PcActiveLog.server_name,
        PcActiveLog.character_name)
            .filter(PcActiveLog.logoff_time.is_(None)))

    return render_template(
        'players/index.html', posts=query)


@socketio.on('connect', namespace='/players_info')
def handle_connect():
    print('Client connected to players_info') 
    
@socketio.on("get_statuses", namespace='/players_info')
def get_statuses():

    # Send the current status to the client
    sid = request.sid
    old_players = get_active_players()
    emit('status_changed', {'data': old_players}, room=sid, namespace='/players_info')
    while True:
        cur_players = get_active_players()
        if cur_players != old_players:
            sid = request.sid
            emit('status_changed', {'data': cur_players}, room=sid)
            old_players = cur_players

        socketio.sleep(1)


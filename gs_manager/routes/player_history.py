from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g
)
from werkzeug.exceptions import abort

from .auth import login_required
from sqlalchemy import (delete, insert)
from ..extensions import db
from ..models.server_nwn import PcActiveLog
from sqlalchemy import null
from ..services.character_service import CharacterService
from flask import request
from .vault_utils import get_vault_url

ph = Blueprint('player_history', __name__)


@ph.route('/player_history')
def index():     
    return render_template(
        'player_history/index.html')


@ph.route('/player_history/data')
def data():
    query = PcActiveLog.query.filter(PcActiveLog.logoff_time.isnot(None))
    data_list = []
    
    for user in query:
        record = user.to_dict()
        
        # Generate vault URL if cd_key is available
        if record.get('cd_key'):
            record['vault_url'] = get_vault_url(record['server_name'], record['cd_key'])
        else:
            record['vault_url'] = None
            
        data_list.append(record)
    
    return {'data': data_list}

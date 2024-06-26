from ..extensions import db
from sqlalchemy import func

# ID |         Player Name |        IP Address |      Character Name | CD Key(s)\n'


class ActivePCs(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    login_time = db.Column(db.TIMESTAMP(timezone=True), server_default=func.now())
    player_name = db.Column(db.String, nullable=False)
    ip = db.Column(db.Integer, nullable=False)
    character_name = db.Column(db.Integer, nullable=False)
    cd_key = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String, nullable=False)

from ..extensions import db
from sqlalchemy import func


class ServerCmds(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer)
    cmd = db.Column(db.String, nullable=False)
    cmd_args = db.Column(db.String, nullable=False)
    cmd_sent_time = db.Column(db.TIMESTAMP(timezone=True), server_default=func.now())
    cmd_executed_time = db.Column(db.TIMESTAMP(timezone=True))



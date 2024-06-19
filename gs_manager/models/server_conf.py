from ..extensions import db
from sqlalchemy import text


class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    server_name = db.Column(db.String, nullable=False)
    max_players = db.Column(db.Integer, nullable=False)
    min_level = db.Column(db.Integer, nullable=False)
    max_level = db.Column(db.Integer, nullable=False)
    pause_play = db.Column(db.Integer, nullable=False)
    pvp = db.Column(db.Integer, nullable=False)
    server_vault = db.Column(db.Integer, nullable=False)
    enforce_legal_char = db.Column(db.Integer, nullable=False)
    item_lv_restrictions = db.Column(db.Integer, nullable=False)
    game_type = db.Column(db.Integer, nullable=False)
    one_party = db.Column(db.Integer, nullable=False)
    difficulty = db.Column(db.Integer, nullable=False)
    auto_save_interval = db.Column(db.Integer, nullable=False)
    player_pwd = db.Column(db.String(80), nullable=False)
    dm_pwd = db.Column(db.String(80), nullable=False)
    admin_pwd = db.Column(db.String(80), nullable=False)
    public_server = db.Column(db.Integer, nullable=False)
    reload_when_empty = db.Column(db.Integer, nullable=False)
    module_name = db.Column(db.String, nullable=False)
    port = db.Column(db.Integer, nullable=False)

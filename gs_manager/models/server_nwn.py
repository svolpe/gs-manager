from ..extensions import db
from sqlalchemy import func


class PcActiveLog(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    player_name = db.Column(db.String,nullable=False)
    character_name = db.Column(db.String,nullable=False)
    ip_addr = db.Column(db.String,nullable=False)
    cd_key = db.Column(db.String,nullable=False)
    docker_name = db.Column(db.String,nullable=False)
    server_name = db.Column(db.String,nullable=False)
    logon_time = db.Column(db.TIMESTAMP(timezone=True), server_default=func.now())
    logoff_time = db.Column(db.TIMESTAMP(timezone=True))


class ServerCmds(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer)
    cmd = db.Column(db.String, nullable=False)
    cmd_args = db.Column(db.String, nullable=False)
    cmd_sent_time = db.Column(db.TIMESTAMP(timezone=True), server_default=func.now())
    cmd_executed_time = db.Column(db.TIMESTAMP(timezone=True))


class ServerConfigs(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    is_active = db.Column(db.Integer, nullable=False)
    database = db.Column(db.Integer, nullable=False)
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


class VolumesDirs(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    active = db.Column(db.Integer, nullable=False)
    volumes_info_id = db.Column(db.Integer, nullable=False)
    dir_src_loc = db.Column(db.String, nullable=False)
    dir_mount_loc = db.Column(db.String, nullable=True)
    read_write = db.Column(db.String, nullable=True)


class VolumesInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)


class ServerVolumes(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    server_configs_id = db.Column(db.Integer, nullable=False)
    volumes_info_id = db.Column(db.Integer, nullable=False)

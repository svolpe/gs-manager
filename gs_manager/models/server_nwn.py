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
    
    def to_dict(self, time_format='%Y-%m-%d %H:%M:%S'):

        return {
            'id': self.id,
            'player_name': self.player_name,
            'character_name': self.character_name,
            'ip_addr': self.ip_addr,
            'cd_key': self.cd_key,
            'docker_name': self.docker_name,
            'server_name': self.server_name,
            'logon_time': self.logon_time,
            'logoff_time': self.logoff_time,
        }

class ServerCmds(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer)
    cmd = db.Column(db.String, nullable=False)
    cmd_args = db.Column(db.String, nullable=False)
    cmd_sent_time = db.Column(db.TIMESTAMP(timezone=True), server_default=func.now())
    cmd_executed_time = db.Column(db.TIMESTAMP(timezone=True))
    cmd_return = db.Column(db.Integer)


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
    def to_dict(self):{
        'id': self.id,
        'is_active': self.is_active,
        'database': self.database,
        'server_name': self.server_name,
        'max_players': self.max_players,
        'min_level': self.min_level,
        'max_level': self.max_level,
        'pause_play': self.pause_play,
        'pvp': self.pvp,
        'server_vault': self.server_vault,
        'enforce_legal_char': self.enforce_legal_char,
        'item_lv_restrictions': self.item_lv_restrictions,
        'game_type': self.game_type,
        'one_party': self.one_party,
        'difficulty': self.difficulty,
        'auto_save_interval': self.auto_save_interval,
        'player_pwd': self.player_pwd,
        'dm_pwd': self.dm_pwd,
        'admin_pwd': self.admin_pwd,
        'public_server': self.public_server,
        'reload_when_empty': self.reload_when_empty,
        'module_name': self.module_name,
        'port': self.port,
    }


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

class ServerStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server_cfg_id = db.Column(db.String, nullable=False, unique=True, index=True)
    status = db.Column(db.String, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'server_cfg_id': self.server_cfg_id,
            'status': self.status,
        }

class SystemWatchdog(db.Model):
    component = db.Column(db.String, nullable=False, unique=True, primary_key=True)
    heart_beat = db.Column(db.TIMESTAMP(timezone=True))


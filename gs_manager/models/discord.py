from ..extensions import db
from sqlalchemy import func


class DiscordChannel(db.Model):
    """A Discord channel (via webhook) that receives notifications for a group of game servers."""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    webhook_url = db.Column(db.String, nullable=False)
    enabled = db.Column(db.Integer, nullable=False, default=1)
    # A watched player does not trigger a new message if they were online in the group within this window
    cooldown_minutes = db.Column(db.Integer, nullable=False, default=30)
    created_at = db.Column(db.TIMESTAMP(timezone=True), server_default=func.now())


class DiscordChannelServer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('discord_channel.id', ondelete='CASCADE'), nullable=False)
    server_cfg_id = db.Column(db.Integer, db.ForeignKey('server_configs.id', ondelete='CASCADE'), nullable=False)
    __table_args__ = (db.UniqueConstraint('channel_id', 'server_cfg_id'),)


class DiscordWatchedPlayer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('discord_channel.id', ondelete='CASCADE'), nullable=False)
    player_name = db.Column(db.String, nullable=False)
    __table_args__ = (db.UniqueConstraint('channel_id', 'player_name'),)


class DiscordNotifyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    channel_id = db.Column(db.Integer, nullable=False)
    player_name = db.Column(db.String)
    character_name = db.Column(db.String)
    server_cfg_id = db.Column(db.Integer)
    sent_time = db.Column(db.TIMESTAMP(timezone=True), server_default=func.now())
    success = db.Column(db.Integer, nullable=False, default=0)
    error = db.Column(db.String)


class DiscordPlayerGroup(db.Model):
    """A named, reusable list of players that channels can watch as a unit."""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False, unique=True)


class DiscordPlayerGroupMember(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    group_id = db.Column(db.Integer, db.ForeignKey('discord_player_group.id', ondelete='CASCADE'), nullable=False)
    player_name = db.Column(db.String, nullable=False)
    __table_args__ = (db.UniqueConstraint('group_id', 'player_name'),)


class DiscordChannelGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('discord_channel.id', ondelete='CASCADE'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('discord_player_group.id', ondelete='CASCADE'), nullable=False)
    __table_args__ = (db.UniqueConstraint('channel_id', 'group_id'),)

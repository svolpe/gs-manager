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
    """A player watched by one channel. Identity is the CD key; names can be changed freely in NWNee."""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('discord_channel.id', ondelete='CASCADE'), nullable=False)
    cd_key = db.Column(db.String, nullable=False)
    # Display-only snapshot of the name when added; matching never uses it
    player_name = db.Column(db.String)
    __table_args__ = (db.UniqueConstraint('channel_id', 'cd_key'),)


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
    cd_key = db.Column(db.String, nullable=False)
    # Display-only snapshot of the name when added; matching never uses it
    player_name = db.Column(db.String)
    __table_args__ = (db.UniqueConstraint('group_id', 'cd_key'),)


class DiscordChannelGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('discord_channel.id', ondelete='CASCADE'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('discord_player_group.id', ondelete='CASCADE'), nullable=False)
    __table_args__ = (db.UniqueConstraint('channel_id', 'group_id'),)


# (table, owner column) pairs whose rows were originally keyed by player name instead of CD key
_NAME_KEYED_TABLES = (('discord_watched_player', 'channel_id'), ('discord_player_group_member', 'group_id'))
# The status-table header gets parsed as a player by the backend; never treat it as a real key
BOGUS_CD_KEYS = ('CD Key(s)',)


def migrate_watch_lists_to_cd_key():
    """One-time move of watched players / group members from name-keyed to CD key-keyed rows.

    Old tables are renamed to <table>_old_v1, the new ones are created, rows are copied with the key backfilled
    from the player's most recent login, and then the old table is dropped. Safe to re-run if interrupted."""
    for table, owner in _NAME_KEYED_TABLES:
        old = f'{table}_old_v1'
        cols = [r[1] for r in db.session.execute(db.text(f'PRAGMA table_info({table})'))]
        if cols and 'cd_key' not in cols:
            db.session.execute(db.text(f'ALTER TABLE {table} RENAME TO {old}'))
            db.session.commit()
    db.create_all()
    for table, owner in _NAME_KEYED_TABLES:
        old = f'{table}_old_v1'
        if not [r for r in db.session.execute(db.text(f'PRAGMA table_info({old})'))]:
            continue
        rows = db.session.execute(db.text(f'SELECT {owner}, player_name FROM {old}')).fetchall()
        for owner_id, name in rows:
            keys = [r[0] for r in db.session.execute(
                db.text('SELECT cd_key FROM pc_active_log WHERE player_name = :n AND cd_key NOT IN :bogus '
                        'GROUP BY cd_key ORDER BY MAX(id) DESC').bindparams(
                    db.bindparam('bogus', expanding=True)),
                {'n': name, 'bogus': list(BOGUS_CD_KEYS)})]
            if not keys:
                print(f"WARNING: discord {table}: no CD key found for '{name}', dropped")
                continue
            if len(keys) > 1:
                print(f"WARNING: discord {table}: '{name}' has used {len(keys)} CD keys {keys}; "
                      f"kept the most recent ({keys[0]}), add the others by key if needed")
            db.session.execute(
                db.text(f'INSERT OR IGNORE INTO {table}({owner}, cd_key, player_name) VALUES(:o, :k, :n)'),
                {'o': owner_id, 'k': keys[0], 'n': name})
        db.session.execute(db.text(f'DROP TABLE {old}'))
        db.session.commit()

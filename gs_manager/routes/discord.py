from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
import re
import requests
from sqlalchemy import func

from .auth import login_required
from .discord_forms import DiscordChannelForm, DiscordPlayerGroupForm
from ..extensions import db
from ..models.server_nwn import ServerConfigs, PcActiveLog
from ..models.discord import DiscordChannel, DiscordChannelServer, DiscordWatchedPlayer, DiscordNotifyLog, \
                              DiscordPlayerGroup, DiscordPlayerGroupMember, DiscordChannelGroup, BOGUS_CD_KEYS

dc = Blueprint('discord', __name__)

CD_KEY_RE = re.compile(r'^[A-Z0-9]{8}$')
DISCORD_WEBHOOK_PREFIXES = ('https://discord.com/api/webhooks/', 'https://discordapp.com/api/webhooks/',
                            'https://canary.discord.com/api/webhooks/', 'https://ptb.discord.com/api/webhooks/')


def _load_choices(form, extra_players=()):
    servers = ServerConfigs.query.order_by(ServerConfigs.server_name).all()
    form.servers.choices = [(s.id, f"{s.server_name} (port {s.port})") for s in servers]
    form.players.choices = _player_choices(extra_players)
    if hasattr(form, 'groups'):
        form.groups.choices = [(g.id, g.name) for g in DiscordPlayerGroup.query.order_by(DiscordPlayerGroup.name)]


def _known_players():
    """CD key -> {'name': latest name, 'aliases': other names ever used}, from the login history, by name."""
    rows = (db.session.query(PcActiveLog.cd_key, PcActiveLog.player_name, func.max(PcActiveLog.id))
            .filter(PcActiveLog.cd_key.notin_(BOGUS_CD_KEYS))
            .group_by(PcActiveLog.cd_key, PcActiveLog.player_name)
            .order_by(func.max(PcActiveLog.id).desc()).all())
    known = {}
    for key, name, _ in rows:
        entry = known.setdefault(key, {'name': name, 'aliases': []})
        if name != entry['name'] and name not in entry['aliases']:
            entry['aliases'].append(name)
    return known


def _player_label(key, known):
    entry = known.get(key)
    if entry is None:
        return f"[{key}] (not seen in login history)"
    label = f"{entry['name']} [{key}]"
    if entry['aliases']:
        label += f" - also: {', '.join(entry['aliases'])}"
    return label


def _player_choices(extra_keys=(), known=None):
    """Picker choices: value is the CD key, label shows the name(s) so it can be searched by username."""
    known = _known_players() if known is None else known
    keys = sorted(known, key=lambda k: known[k]['name'].lower())
    keys += [k for k in dict.fromkeys(extra_keys) if k not in known]
    return [(k, _player_label(k, known)) for k in keys]


def _parse_keys(text):
    """Split a free-text box into CD keys. Returns (keys, invalid_tokens)."""
    keys, invalid = [], []
    for token in re.split(r'[\s,;]+', text or ''):
        if not token:
            continue
        token = token.upper()
        (keys if CD_KEY_RE.match(token) else invalid).append(token)
    return keys, invalid


def _collect_keys(form):
    """Selected players plus typed-in keys. Flashes and returns None if a typed key is malformed."""
    extra, invalid = _parse_keys(form.extra_keys.data)
    if invalid:
        flash(f"Not a valid CD key (expected 8 letters/digits): {', '.join(invalid)}")
        return None
    return list(dict.fromkeys(list(form.players.data or []) + extra))


def _save_links(channel_id, server_ids, player_keys, group_ids):
    DiscordChannelServer.query.filter_by(channel_id=channel_id).delete()
    DiscordWatchedPlayer.query.filter_by(channel_id=channel_id).delete()
    DiscordChannelGroup.query.filter_by(channel_id=channel_id).delete()
    for gid in set(group_ids):
        db.session.add(DiscordChannelGroup(channel_id=channel_id, group_id=gid))
    for sid in set(server_ids):
        db.session.add(DiscordChannelServer(channel_id=channel_id, server_cfg_id=sid))
    known = _known_players()
    for key in player_keys:
        db.session.add(DiscordWatchedPlayer(channel_id=channel_id, cd_key=key,
                                            player_name=known[key]['name'] if key in known else None))


def _valid_webhook(url):
    return url.startswith(DISCORD_WEBHOOK_PREFIXES)


@dc.route('/discord')
@login_required
def index():
    channels = DiscordChannel.query.order_by(DiscordChannel.name).all()
    rows = []
    for c in channels:
        rows.append({
            'channel': c,
            'servers': DiscordChannelServer.query.filter_by(channel_id=c.id).count(),
            'players': DiscordWatchedPlayer.query.filter_by(channel_id=c.id).count(),
            'groups': DiscordChannelGroup.query.filter_by(channel_id=c.id).count(),
        })
    return render_template('discord/index.html', rows=rows)


@dc.route('/discord/create', methods=('GET', 'POST'))
@login_required
def create():
    form = DiscordChannelForm()
    _load_choices(form, extra_players=list(form.players.data or []))
    if request.method == 'POST' and form.validate_on_submit():
        keys = _collect_keys(form)
        if not _valid_webhook(form.webhook_url.data):
            flash('Webhook URL must be a Discord webhook (https://discord.com/api/webhooks/...).')
        elif keys is not None:
            channel = DiscordChannel(name=form.name.data, webhook_url=form.webhook_url.data,
                                     enabled=int(form.enabled.data), cooldown_minutes=form.cooldown_minutes.data)
            db.session.add(channel)
            db.session.flush()
            _save_links(channel.id, form.servers.data, keys, form.groups.data)
            db.session.commit()
            return redirect(url_for('discord.index'))
    elif request.method == 'GET':
        form.enabled.data = True
    return render_template('discord/edit.html', form=form, channel=None)


@dc.route('/discord/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    channel = db.session.get(DiscordChannel, id)
    if channel is None:
        abort(404, f"Discord channel {id} doesn't exist.")

    watched = [w.cd_key for w in DiscordWatchedPlayer.query.filter_by(channel_id=id)]
    form = DiscordChannelForm()
    _load_choices(form, extra_players=watched + list(form.players.data or []))

    if request.method == 'POST' and form.validate_on_submit():
        keys = _collect_keys(form)
        if not _valid_webhook(form.webhook_url.data):
            flash('Webhook URL must be a Discord webhook (https://discord.com/api/webhooks/...).')
        elif keys is not None:
            channel.name = form.name.data
            channel.webhook_url = form.webhook_url.data
            channel.enabled = int(form.enabled.data)
            channel.cooldown_minutes = form.cooldown_minutes.data
            _save_links(id, form.servers.data, keys, form.groups.data)
            db.session.commit()
            return redirect(url_for('discord.index'))
    elif request.method == 'GET':
        form.name.data = channel.name
        form.webhook_url.data = channel.webhook_url
        form.enabled.data = bool(channel.enabled)
        form.cooldown_minutes.data = channel.cooldown_minutes
        form.servers.data = [s.server_cfg_id for s in DiscordChannelServer.query.filter_by(channel_id=id)]
        form.players.data = watched
        form.groups.data = [g.group_id for g in DiscordChannelGroup.query.filter_by(channel_id=id)]
    return render_template('discord/edit.html', form=form, channel=channel)


@dc.route('/discord/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    DiscordChannelServer.query.filter_by(channel_id=id).delete()
    DiscordWatchedPlayer.query.filter_by(channel_id=id).delete()
    DiscordChannelGroup.query.filter_by(channel_id=id).delete()
    DiscordChannel.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect(url_for('discord.index'))


@dc.route('/discord/<int:id>/test', methods=['POST'])
@login_required
def test(id):
    channel = db.session.get(DiscordChannel, id)
    if channel is None:
        abort(404, f"Discord channel {id} doesn't exist.")
    try:
        resp = requests.post(channel.webhook_url,
                             json={'content': 'Test message from GS Manager', 'allowed_mentions': {'parse': []}},
                             timeout=10)
        if resp.status_code in (200, 204):
            flash(f'Test message sent to "{channel.name}".')
        else:
            flash(f'Discord returned HTTP {resp.status_code}: {resp.text[:200]}')
    except requests.RequestException as e:
        flash(f'Could not reach Discord: {e}')
    return redirect(url_for('discord.index'))


@dc.route('/discord/log')
@login_required
def log():
    channels = {c.id: c.name for c in DiscordChannel.query.all()}
    servers = {s.id: s.server_name for s in ServerConfigs.query.all()}
    entries = DiscordNotifyLog.query.order_by(DiscordNotifyLog.id.desc()).limit(500).all()
    rows = [{
        'time': e.sent_time,
        'channel': channels.get(e.channel_id, f'(deleted {e.channel_id})'),
        'player': e.player_name,
        'character': e.character_name,
        'server': servers.get(e.server_cfg_id, e.server_cfg_id),
        'success': bool(e.success),
        'error': e.error or '',
    } for e in entries]
    return render_template('discord/log.html', rows=rows)


@dc.route('/discord/groups')
@login_required
def groups():
    rows = []
    known = _known_players()
    for g in DiscordPlayerGroup.query.order_by(DiscordPlayerGroup.name).all():
        members = [known[m.cd_key]['name'] + f' [{m.cd_key}]' if m.cd_key in known
                   else f"{m.player_name or '?'} [{m.cd_key}]"
                   for m in DiscordPlayerGroupMember.query.filter_by(group_id=g.id)]
        members.sort(key=str.lower)
        rows.append({'group': g, 'members': members,
                     'channels': DiscordChannelGroup.query.filter_by(group_id=g.id).count()})
    return render_template('discord/groups.html', rows=rows)


def _save_group_members(group_id, player_keys):
    DiscordPlayerGroupMember.query.filter_by(group_id=group_id).delete()
    known = _known_players()
    for key in player_keys:
        db.session.add(DiscordPlayerGroupMember(group_id=group_id, cd_key=key,
                                                player_name=known[key]['name'] if key in known else None))


def _group_name_taken(name, exclude_id=None):
    q = DiscordPlayerGroup.query.filter(DiscordPlayerGroup.name == name)
    if exclude_id is not None:
        q = q.filter(DiscordPlayerGroup.id != exclude_id)
    return q.first() is not None


@dc.route('/discord/groups/create', methods=('GET', 'POST'))
@login_required
def group_create():
    form = DiscordPlayerGroupForm()
    form.players.choices = _player_choices(form.players.data or [])
    if request.method == 'POST' and form.validate_on_submit():
        keys = _collect_keys(form)
        if _group_name_taken(form.name.data):
            flash('A group with that name already exists.')
        elif keys is not None:
            group = DiscordPlayerGroup(name=form.name.data)
            db.session.add(group)
            db.session.flush()
            _save_group_members(group.id, keys)
            db.session.commit()
            return redirect(url_for('discord.groups'))
    return render_template('discord/group_edit.html', form=form, group=None)


@dc.route('/discord/groups/<int:id>/update', methods=('GET', 'POST'))
@login_required
def group_update(id):
    group = db.session.get(DiscordPlayerGroup, id)
    if group is None:
        abort(404, f"Player group {id} doesn't exist.")
    members = [m.cd_key for m in DiscordPlayerGroupMember.query.filter_by(group_id=id)]
    form = DiscordPlayerGroupForm()
    form.players.choices = _player_choices(members + list(form.players.data or []))
    if request.method == 'POST' and form.validate_on_submit():
        keys = _collect_keys(form)
        if _group_name_taken(form.name.data, exclude_id=id):
            flash('A group with that name already exists.')
        elif keys is not None:
            group.name = form.name.data
            _save_group_members(id, keys)
            db.session.commit()
            return redirect(url_for('discord.groups'))
    elif request.method == 'GET':
        form.name.data = group.name
        form.players.data = members
    return render_template('discord/group_edit.html', form=form, group=group)


@dc.route('/discord/groups/<int:id>/delete', methods=['POST'])
@login_required
def group_delete(id):
    DiscordChannelGroup.query.filter_by(group_id=id).delete()
    DiscordPlayerGroupMember.query.filter_by(group_id=id).delete()
    DiscordPlayerGroup.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect(url_for('discord.groups'))

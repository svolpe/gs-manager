import os
import subprocess

from flask import Blueprint, render_template, request, jsonify, current_app

from .auth import login_required
from ..models.server_nwn import ServerConfigs, VolumesDirs

lg = Blueprint('logs', __name__)

DEFAULT_UNITS = ['gsmanager', 'nwneebackend']
DEFAULT_MAX_LINES = 5000
LOG_EXTENSIONS = ('.log', '.txt')
MAX_FILE_LISTING = 500
MAX_FILE_DEPTH = 3
# Never read more than this many bytes from the end of a file, however long the lines are
MAX_TAIL_BYTES = 2 * 1024 * 1024


class LogError(Exception):
    """An error that should be shown to the user as text rather than as a 500"""


def _max_lines():
    return current_app.config.get('LOG_MAX_LINES', DEFAULT_MAX_LINES)


def _allowed_units():
    return list(current_app.config.get('LOG_SYSTEMD_UNITS', DEFAULT_UNITS))


def _clamp_lines(value):
    try:
        lines = int(value)
    except (TypeError, ValueError):
        lines = 500
    return max(1, min(lines, _max_lines()))


def _docker_client():
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return client
    except Exception as e:
        raise LogError("Could not connect to docker: {0}".format(e))


def _run(cmd):
    """Run a command (argument list, no shell) and return its output as text"""
    try:
        res = subprocess.run(cmd, capture_output=True, timeout=10)
    except FileNotFoundError:
        raise LogError("{0} is not installed on this host".format(cmd[0]))
    except subprocess.TimeoutExpired:
        raise LogError("{0} timed out".format(cmd[0]))
    out = res.stdout.decode(errors='replace')
    err = res.stderr.decode(errors='replace')
    if res.returncode != 0:
        raise LogError(err.strip() or "{0} exited with code {1}".format(cmd[0], res.returncode))
    # journalctl prints warnings (e.g. missing permission to see other users' logs) on stderr
    return out + (("\n" + err) if err.strip() and not out.strip() else "")


def _container_logs(cfg_id, lines):
    try:
        cfg_id = int(cfg_id)
    except (TypeError, ValueError):
        raise LogError("Invalid server id")
    if ServerConfigs.query.filter_by(id=cfg_id).first() is None:
        raise LogError("Unknown server id")

    client = _docker_client()
    try:
        container = client.containers.get("nwn_{0}".format(cfg_id))
    except Exception as e:
        raise LogError("Container nwn_{0} not found: {1}".format(cfg_id, e))
    return container.logs(tail=lines, timestamps=True).decode(errors='replace')


def _journal_logs(unit, lines):
    # Only units on the allowlist (plus docker, for the daemon view) can be requested
    if unit not in _allowed_units() + ['docker']:
        raise LogError("Unit is not in LOG_SYSTEMD_UNITS")
    return _run(['journalctl', '-u', unit, '-n', str(lines), '--no-pager', '-o', 'short-iso'])


def _docker_status():
    client = _docker_client()
    rows = ["{:<14} {:<28} {:<14} {}".format("NAME", "IMAGE", "STATE", "STATUS / EXIT")]
    for c in sorted(client.containers.list(all=True), key=lambda c: c.name):
        state = c.attrs.get('State', {})
        tags = c.image.tags[0] if c.image.tags else c.attrs.get('Config', {}).get('Image', '?')
        detail = c.status
        if state.get('Status') != 'running':
            detail = "exit {0} at {1} {2}".format(state.get('ExitCode'), state.get('FinishedAt', '?'),
                                                  state.get('Error', ''))
        rows.append("{:<14} {:<28} {:<14} {}".format(c.name, tags, c.status, detail))
    return "\n".join(rows)


def _dir_roots():
    """Map of volume directory id -> real host path, for directories that exist"""
    roots = {}
    for d in VolumesDirs.query.all():
        real = os.path.realpath(d.dir_src_loc)
        if os.path.isdir(real):
            roots[d.id] = real
    return roots


def _inside(path, root):
    return os.path.commonpath([path, root]) == root


def _list_log_files():
    files = []
    for dir_id, root in _dir_roots().items():
        for cur, dirs, names in os.walk(root, followlinks=False):
            depth = cur[len(root):].count(os.sep)
            if depth >= MAX_FILE_DEPTH:
                dirs[:] = []
            for name in names:
                if name.lower().endswith(LOG_EXTENSIONS):
                    rel = os.path.relpath(os.path.join(cur, name), root)
                    files.append({'id': "{0}:{1}".format(dir_id, rel), 'name': "{0}: {1}".format(
                        os.path.basename(root), rel)})
                    if len(files) >= MAX_FILE_LISTING:
                        return files
    return sorted(files, key=lambda f: f['name'])


def _resolve_log_file(file_id):
    """Turn a '<dir id>:<relative path>' id into a real path, refusing anything outside the volume dir"""
    try:
        dir_id, rel = file_id.split(':', 1)
        root = _dir_roots()[int(dir_id)]
    except (ValueError, KeyError, AttributeError):
        raise LogError("Unknown log file")
    real = os.path.realpath(os.path.join(root, rel))
    if not _inside(real, root) or not os.path.isfile(real) or not real.lower().endswith(LOG_EXTENSIONS):
        raise LogError("Unknown log file")
    return real


def _tail_file(path, lines):
    with open(path, 'rb') as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        start = max(0, size - MAX_TAIL_BYTES)
        f.seek(start)
        data = f.read()
    text = data.decode(errors='replace').splitlines()
    if start > 0 and text:
        text = text[1:]  # first line is probably cut off
    return "\n".join(text[-lines:])


@lg.route('/logs')
@login_required
def index():
    return render_template('logs/index.html')


@lg.route('/logs/sources')
@login_required
def sources():
    containers = [{'id': str(c.id), 'name': "{0} (nwn_{1})".format(c.server_name, c.id)}
                  for c in ServerConfigs.query.order_by(ServerConfigs.id).all()]
    return jsonify({
        'container': containers,
        'journal': [{'id': u, 'name': u} for u in _allowed_units()],
        'file': _list_log_files(),
        'docker': [{'id': 'status', 'name': 'Container status'},
                   {'id': 'daemon', 'name': 'Docker service log'}],
        'max_lines': _max_lines(),
    })


@lg.route('/logs/data')
@login_required
def data():
    log_type = request.args.get('type', '')
    source = request.args.get('id', '')
    lines = _clamp_lines(request.args.get('lines'))
    try:
        if log_type == 'container':
            text = _container_logs(source, lines)
        elif log_type == 'journal':
            text = _journal_logs(source, lines)
        elif log_type == 'file':
            text = _tail_file(_resolve_log_file(source), lines)
        elif log_type == 'docker' and source == 'status':
            text = _docker_status()
        elif log_type == 'docker' and source == 'daemon':
            text = _journal_logs('docker', lines)
        else:
            raise LogError("Unknown log source")
        return jsonify({'ok': True, 'text': text})
    except LogError as e:
        return jsonify({'ok': False, 'text': str(e)})
    except Exception as e:
        current_app.logger.exception("log viewer failed")
        return jsonify({'ok': False, 'text': "Unexpected error: {0}".format(e)})

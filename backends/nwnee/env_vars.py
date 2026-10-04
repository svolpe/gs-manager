"""Parsing/validation of the per-server "extra environment variables" text (one KEY=value per line).

Used by both the Flask app (validate on save) and the backend daemon (apply to the container). It must stay free of
Flask/gevent imports so the daemon can import it.
"""
import re

# Variables owned by the server config form. Setting them in the free-text box would silently fight the form
# fields, so they are rejected on save and ignored by the backend.
MANAGED_ENV_KEYS = frozenset({
    'NWN_PORT', 'NWN_MODULE', 'NWN_SERVERNAME', 'NWN_PUBLICSERVER', 'NWN_MAXCLIENTS', 'NWN_MINLEVEL',
    'NWN_MAXLEVEL', 'NWN_PAUSEANDPLAY', 'NWN_PVP', 'NWN_SERVERVAULT', 'NWN_ELC', 'NWN_ILR', 'NWN_GAMETYPE',
    'NWN_ONEPARTY', 'NWN_DIFFICULTY', 'NWN_AUTOSAVEINTERVAL', 'NWN_RELOADWHENEMPTY', 'NWN_PLAYERPASSWORD',
    'NWN_DMPASSWORD', 'NWN_ADMINPASSWORD',
})

_NAME_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def parse_env_text(text):
    """Parse KEY=value lines.

    Blank lines and lines starting with '#' are ignored, an optional leading 'export ' is allowed, and surrounding
    whitespace/matching quotes around a value are stripped. If a name appears more than once the last one wins.

    Returns (env, errors, warnings): env is a dict, errors and warnings are lists of 'line N: ...' strings."""
    env, errors, warnings, seen = {}, [], [], {}
    for lineno, raw in enumerate((text or '').splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[len('export '):].lstrip()
        name, sep, value = line.partition('=')
        name, value = name.strip(), value.strip()
        if not sep:
            errors.append(f"line {lineno}: expected KEY=value")
            continue
        if not _NAME_RE.match(name):
            errors.append(f"line {lineno}: '{name}' is not a valid variable name")
            continue
        if name in MANAGED_ENV_KEYS:
            errors.append(f"line {lineno}: {name} is set by the server settings above and can't be overridden here")
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if name in seen:
            warnings.append(f"line {lineno}: {name} was already set on line {seen[name]}, the last value is used")
        seen[name] = lineno
        env[name] = value
    return env, errors, warnings

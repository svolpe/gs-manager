import queue
import re
import threading
import time

import requests

import db

_queue = queue.Queue()
_MD_SPECIAL = re.compile(r'([\\*_`~|>:])')


def _escape(text):
    """Escape Discord markdown so names can't break formatting."""
    return _MD_SPECIAL.sub(r'\\\1', str(text))


def _log(channel_id, player, character, server_cfg_id, success, error=None):
    try:
        db.sql_update("INSERT INTO discord_notify_log(channel_id, player_name, character_name, server_cfg_id, "
                      "sent_time, success, error) VALUES(?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)",
                      (channel_id, player, character, server_cfg_id, int(success), error))
    except Exception as e:
        print(f"ERROR: could not write discord_notify_log: {e}")


def _post(item):
    payload = {'content': item['content'], 'allowed_mentions': {'parse': []}}
    for attempt in range(2):
        try:
            resp = requests.post(item['webhook_url'], json=payload, timeout=10)
        except requests.RequestException as e:
            return False, str(e)[:300]
        if resp.status_code in (200, 204):
            return True, None
        if resp.status_code == 429 and attempt == 0:
            try:
                wait = float(resp.json().get('retry_after', 1))
            except Exception:
                wait = 1
            time.sleep(min(wait, 30))
            continue
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    return False, "rate limited"


def sender_thread(stop_flag):
    """Worker that posts queued messages so slow/failed HTTP calls never block the backend main loop."""
    while not stop_flag.is_set():
        try:
            item = _queue.get(timeout=1)
        except queue.Empty:
            continue
        try:
            ok, err = _post(item)
            _log(item['channel_id'], item['player'], item['character'], item['server_cfg_id'], ok, err)
            if not ok:
                print(f"ERROR: discord notification failed: {err}")
        except Exception as e:
            print(f"ERROR: discord sender: {e}")


def start_sender(stop_flag):
    thread = threading.Thread(target=sender_thread, args=(stop_flag,), daemon=True)
    thread.start()
    return thread


def handle_logins(new_logins):
    """new_logins: list of dicts with player_name, character_name, cd_key, server_cfg_id, server_name.

    Must be called after the new rows were inserted into pc_active_log."""
    for login in new_logins:
        channels = db.sql_query(
            "SELECT c.id, c.webhook_url, c.cooldown_minutes FROM discord_channel c "
            "JOIN discord_channel_server cs ON cs.channel_id = c.id "
            "WHERE c.enabled = 1 AND cs.server_cfg_id = ? AND ("
            "  EXISTS (SELECT 1 FROM discord_watched_player wp "
            "          WHERE wp.channel_id = c.id AND wp.player_name = ?) "
            "  OR EXISTS (SELECT 1 FROM discord_channel_group cg "
            "             JOIN discord_player_group_member m ON m.group_id = cg.group_id "
            "             WHERE cg.channel_id = c.id AND m.player_name = ?))",
            (login['server_cfg_id'], login['player_name'], login['player_name']))
        for ch in channels:
            group = db.sql_query("SELECT server_cfg_id FROM discord_channel_server WHERE channel_id = ?", (ch['id'],))
            docker_names = ['nwn_' + str(g['server_cfg_id']) for g in group]
            marks = ','.join('?' * len(docker_names))
            cutoff = f"-{int(ch['cooldown_minutes'])} minutes"
            # Suppress if the player is already online elsewhere in the group, or was online there recently
            recent = db.sql_query(
                f"SELECT 1 FROM pc_active_log WHERE player_name = ? AND docker_name IN ({marks}) "
                "AND ((logoff_time IS NULL AND cd_key != ?) OR logoff_time >= datetime('now', ?)) LIMIT 1",
                (login['player_name'], *docker_names, login['cd_key'], cutoff))
            if recent:
                continue
            content = (f"\U0001F7E2 **{_escape(login['player_name'])}** is online as "
                       f"*{_escape(login['character_name'])}* on **{_escape(login['server_name'])}**")
            _queue.put({'channel_id': ch['id'], 'webhook_url': ch['webhook_url'], 'content': content,
                        'player': login['player_name'], 'character': login['character_name'],
                        'server_cfg_id': login['server_cfg_id']})

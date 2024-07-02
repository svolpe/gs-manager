import sqlite3
import os

DBPATH = 'instance/gsmanager.sqlite'


def set_cmd_executed(cmd_id):
    con = sqlite3.connect(DBPATH)
    cur = con.cursor()
    query = "update server_cmds set cmd_executed_time = DATETIME('now','localtime') where id = ?"
    cur.execute(query, (cmd_id,))
    con.commit()
    con.close()


def sql_update_many(query, data):
    con = sqlite3.connect(DBPATH)
    cur = con.cursor()
    cur.executemany(query, data)
    con.commit()
    con.close()


def sql_data_to_list_of_dicts(select_query):
    """Returns data from an SQL query as a list of dicts."""
    con = sqlite3.connect(DBPATH)
    try:
        con.row_factory = sqlite3.Row
        things = con.execute(select_query).fetchall()
        unpacked = [{k: item[k] for k in item.keys()} for item in things]

        return unpacked
    except Exception as e:
        print(f"Failed to execute. Query: {select_query}\n with error:\n{e}")
        return {}
    finally:
        con.close()


def sql_data_return_dict_of_dict(dict_key, select_query):
    con = sqlite3.connect(DBPATH)
    try:
        con.row_factory = sqlite3.Row
        things = con.execute(select_query).fetchall()
        users = dict()
        for item in things:
            item = {k: item[k] for k in item.keys()}
            cd_key = item[dict_key]
            del (item[dict_key])
            users[cd_key] = item
        return users
    except Exception as e:
        print(f"Failed to execute. Query: {select_query}\n with error:\n{e}")
        return {}
    finally:
        con.close()


def get_volumes(cfg_id):
    volumes = sql_data_to_list_of_dicts("select sv.server_configs_id, vd.dir_mount_loc, vd.dir_src_loc, vd.read_write "
                                        "from server_volumes as sv "
                                        "inner join volumes_dirs as vd "
                                        "on sv.volumes_info_id=vd.volumes_info_id "
                                        f"where sv.server_configs_id={cfg_id}")
    volumes_data = dict()
    for volume in volumes:
        volumes_data[volume['dir_src_loc']] = {'bind': volume['dir_mount_loc'], 'mode': volume['read_write']}

    return volumes_data

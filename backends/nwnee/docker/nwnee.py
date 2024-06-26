from backends.nwnee.docker.nwn_docker import NwnServer
import docker
import sqlite3
import time

DBPATH = 'instance/gsmanager.sqlite'


def update_users_sql(last_active, current_active):
    pass


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


if __name__ == "__main__":
    servers = dict()

    client = docker.APIClient()

    server_cfgs = sql_data_to_list_of_dicts("SELECT * FROM Config")

    for cfg in server_cfgs:
        docker_name = "nwn_" + str(cfg['id'])

        server = NwnServer(cfg, docker_name=docker_name)

        if cfg['is_active'] == 1:
            server.create_container()
            server.start()

        servers[str(cfg['id'])] = server

    get_users_timer_start = time.time()
    while True:
        # Get all commands that have not yet been run
        server_cmds = sql_data_to_list_of_dicts("SELECT * FROM server_cmds where cmd_executed_time is NULL")
        for cmd in server_cmds:
            if cmd['cmd'] == 'start':
                servers[cmd['cmd_args']].start()
                set_cmd_executed(cmd['id'])

            elif cmd['cmd'] == 'stop':
                servers[cmd['cmd_args']].stop()
                set_cmd_executed(cmd['id'])

            elif cmd['cmd'] == 'create':
                server_cfg = sql_data_to_list_of_dicts("SELECT * FROM Config where id = " + str(cmd['cmd_args']))[0]
                docker_name = "nwn_" + str(server_cfg['id'])
                server = NwnServer(cfg, docker_name=docker_name)
                server.create_container()
                server.start()
                servers[cmd['cmd_args']] = server

            elif cmd['cmd'] == 'delete':

                servers[cmd['cmd_args']].remove_container()
                del servers[cmd['cmd_args']]
                set_cmd_executed(cmd['id'])

        # TODO: insert update active user list
        active_users = dict()

        # Get users!
        if (time.time() - get_users_timer_start) > 5:
            for key in servers:
                server = servers[key]

                status = server.container_status()
                if status == 'running':
                    active_users.update(server.get_active_users())
                    if len(active_users) > 0:
                        i = 1 + 1

            get_users_timer_start = time.time()

            last_active_users = sql_data_return_dict_of_dict("cd_key",
                                                             "SELECT * FROM pc_active_log "
                                                             "where logoff_time is NULL")

            # TODO: The update/insert users code needs to be seriously refactored
            # Update users table
            if len(last_active_users) or len(active_users):
                insert_users = dict()
                update_users = dict()
                insert_data = list()
                update_data = list()
                logoff_data = list()

                # Get combined list of active and last active users
                all_user_keys = list(set(list(active_users.keys()) + list(last_active_users.keys())))
                for key in all_user_keys:
                    # New keys (players) to insert into the user database
                    if key not in last_active_users:
                        insert_users.update(active_users)
                        user = active_users[key]
                        insert_data.append((key, user['player_name'], user['char_name'], user['ip'],
                                            user['docker_name']))
                    # Users that are on-going active and need to be updated
                    elif key in active_users:
                        a_user = active_users[key]
                        l_user = last_active_users[key]
                        if (a_user['character_name'] != l_user['character_name']
                                or a_user['docker_name'] != l_user['docker_name']):
                            user = active_users[key]
                            update_data.append((user['player_name'], user['character_name'], user['ip_addr'],
                                                user['docker_name'], key))
                    # All remaining ones need to be set as logged off
                    else:
                        logoff_data.append((key,))
                if len(insert_data):
                    query = '''insert into pc_active_log(cd_key, player_name, character_name, ip_addr, docker_name)
                            values(?, ?, ?, ?, ?)'''
                    sql_update_many(query, insert_data)
                if len(update_data):
                    query = '''update pc_active_log set player_name=?, character_name=?, ip_addr=?, docker_name=?
                                where cd_key = ?'''
                    sql_update_many(query, update_data)
                if len(logoff_data):
                    query = '''update pc_active_log set logoff_time = CURRENT_TIMESTAMP where cd_key = ?'''
                    sql_update_many(query, logoff_data)

        # Sleep to release the CPU for other processing
        time.sleep(1)

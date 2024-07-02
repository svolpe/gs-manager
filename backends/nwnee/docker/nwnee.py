from backends.nwnee.docker.nwn_docker import NwnServer
import docker
import time
import db

if __name__ == "__main__":
    servers = dict()

    client = docker.APIClient()

    server_cfgs = db.sql_data_to_list_of_dicts("SELECT * FROM server_configs")

    t1 = time.time()
    for cfg in server_cfgs:
        docker_name = "nwn_" + str(cfg['id'])

        server = NwnServer(cfg, docker_name=docker_name)

        if cfg['is_active'] == 1:
            server.create_container()
            server.start()

        servers[str(cfg['id'])] = server

    print(f"Time to initialize docker images: {round(time.time() - t1, 1)}s")

    get_users_timer_start = time.time()
    while True:
        # Get all commands that have not yet been run
        server_cmds = db.sql_data_to_list_of_dicts("SELECT * FROM server_cmds where cmd_executed_time is NULL")
        for cmd in server_cmds:

            if cmd['cmd'] == 'recreate':
                # stop existing container
                servers[cmd['cmd_args']].stop()
                servers[cmd['cmd_args']].remove_container()

                cfg = db.sql_data_to_list_of_dicts(f"SELECT * FROM config where id = {cmd['cmd_args']}")
                # TODO: the current way of setting the docker name needs to be cleaned up!
                docker_name = "nwn_" + str(cfg['id'])
                servers[cmd['cmd_args']] = NwnServer(cfg, docker_name=docker_name)

                servers[cmd['cmd_args']].start()
                db.set_cmd_executed(cmd['id'])

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

            last_active_users = db.sql_data_return_dict_of_dict("cd_key",
                                                                "SELECT * FROM pc_active_log "
                                                                "where logoff_time is NULL")

            # TODO: The update/insert users code needs to be seriously refactored
            # Update users table
            if len(last_active_users) or len(active_users):
                insert_data = list()
                update_data = list()
                logoff_data = list()

                # Get combined list of active and last active users
                all_user_keys = list(set(list(active_users.keys()) + list(last_active_users.keys())))
                for key in all_user_keys:
                    # New keys (players) to insert into the user database
                    if key not in last_active_users:
                        user = active_users[key]
                        insert_data.append((key, user['player_name'], user['character_name'], user['ip_addr'],
                                            user['docker_name'], user['server_name']))
                    # Users that are on-going active and need to be updated
                    elif key in active_users:
                        a_user = active_users[key]
                        l_user = last_active_users[key]
                        if (a_user['character_name'] != l_user['character_name']
                                or a_user['docker_name'] != l_user['docker_name']):
                            user = active_users[key]
                            update_data.append((user['player_name'], user['character_name'], user['ip_addr'],
                                                user['docker_name'], user['server_name'], key))
                    # All remaining ones need to be set as logged off
                    else:
                        logoff_data.append((key,))
                if len(insert_data):
                    query = '''insert into pc_active_log(cd_key, player_name, character_name, ip_addr, docker_name, 
                            server_name) values(?, ?, ?, ?, ?, ?)'''
                    db.sql_update_many(query, insert_data)
                if len(update_data):
                    query = '''update pc_active_log set player_name=?, character_name=?, ip_addr=?, docker_name=?, 
                    server_name=? where cd_key = ?'''
                    db.sql_update_many(query, update_data)
                if len(logoff_data):
                    query = '''update pc_active_log set logoff_time = CURRENT_TIMESTAMP where cd_key = ?'''
                    db.sql_update_many(query, logoff_data)

        # Sleep to release the CPU for other processing
        time.sleep(1)

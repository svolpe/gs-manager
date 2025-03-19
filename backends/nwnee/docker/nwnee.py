from backends.nwnee.docker.nwn_docker import NwnServer
import docker
import time
import db
from backends.nwnee.config import ProductionConfig as backend_config
import threading

#This thread function currently checks for new start/stop commands
# and marks them as stopping or starting to make the reaction time for
# the UI quicker. Eventually all of the command processing should be put
# into this thread to make it cleaner.

def check_cmds_thread(flag):
    while not flag.is_set():
        cmds = db.get_new_commands()
        for cmd in cmds:
            exec_cmd = cmd['cmd']
            server_id = cmd['cmd_args']
            if exec_cmd == 'stop':
                db.set_status('stopping', server_id)
            elif exec_cmd == 'start':
                db.set_status('starting', server_id)
        time.sleep(1)
    
if __name__ == "__main__":
    
    stop_flag = threading.Event()
    thread = threading.Thread(target=check_cmds_thread, args=(stop_flag,))
    thread.start()
    servers = {}
    
    while True:
        try:
            client = docker.APIClient()
            break
        except:
            print("ERROR: Could not connect to docker Client!")
        time.sleep(1)
    
    server_cfgs = db.sql_data_to_list_of_dicts("SELECT * FROM server_configs")

    t1 = time.time()
    for cfg in server_cfgs:
        docker_name = "nwn_" + str(cfg['id'])

        server = NwnServer(backend_config, cfg, docker_name=docker_name)

        if cfg['is_active'] == 1:
            server.create_container()
            server.start()
        servers[str(cfg['id'])] = server

    print(f"Time to initialize docker images: {round(time.time() - t1, 1)}s")

    get_users_timer_start = time.time()
    
    #flush old commands that were not yet run
    db.flush_unexecuted_cmds()

    while True:
        db.update_heartbeat('backend_nwn')
        # Get all commands that have not yet been run
        server_cmds = db.get_new_commands()
        for cmd in server_cmds:
            cmd_id = cmd['id']
            exec_cmd = cmd['cmd']
            if exec_cmd == 'stop':
                server_id = cmd['cmd_args']
                try:
                    servers[server_id].stop()
                except:
                    print("ERROR: Tried to stop a server that is not running")
                    db.set_cmd_executed(cmd_id, -1)
                
                #Determine stopped reason
                servers[server_id].remove_container()
                del servers[server_id]
                db.set_cmd_executed(cmd_id)
                
                db.set_status('stopped', server_id)

            if exec_cmd == 'start':
                server_id = cmd['cmd_args']
                cfg = db.sql_data_to_list_of_dicts(f"SELECT * FROM server_configs where id = {server_id}")[0]
                # TODO: the current way of setting the docker name needs to be cleaned up!
                docker_name = "nwn_" + str(server_id)
                server = NwnServer(backend_config, cfg, docker_name=docker_name)
                server.create_container()
                
                #Set to active in case default was not active
                server.server_cfg['is_active'] = 1
                server.start()

                servers[server_id] = server
                db.set_cmd_executed(cmd_id)

        # TODO: insert update active user list
        active_users = dict()

        # Send server statuses
        for key in servers.keys():
            server = servers[key]
            # Get Status and set it all to lower case just in case.
            status = server.container_status().lower()
            db.set_status(status, key)

        # Get users!
        if (time.time() - get_users_timer_start) > 5:
            for key in servers:
                server = servers[key]

                status = server.container_status()
                if status == 'running':
                    active_users.update(server.get_active_users())

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
                                                user['docker_name'], user['server_name'], key, last_active_users[key]['id']))
                    # All remaining ones need to be set as logged off
                    else:
                        logoff_data.append((last_active_users[key]['id'],))
                if len(insert_data):
                    query = '''insert into pc_active_log(cd_key, player_name, character_name, ip_addr, docker_name, 
                            server_name) values(?, ?, ?, ?, ?, ?)'''
                    db.sql_update_many(query, insert_data)
                if len(update_data):
                    query = '''update pc_active_log set player_name=?, character_name=?, ip_addr=?, docker_name=?, 
                    server_name=?, cd_key = ? where id = ?'''
                    db.sql_update_many(query, update_data)
                if len(logoff_data):
                    query = '''update pc_active_log set logoff_time = CURRENT_TIMESTAMP where id = ?'''
                    db.sql_update_many(query, logoff_data)

        # Sleep to release the CPU for other processing
        time.sleep(1)


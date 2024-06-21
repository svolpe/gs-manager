import docker, time, select

# TODO: It might make sense to remove all the low level string manipulation/extraction methods into their own class


class NwnServer:
    def __init__(self, server_cfg, image_name='nwnxee/unified', network='host'):
        self._load_cfg(server_cfg)
        self.client = docker.APIClient()
        cfg_host = self.client.create_host_config(network_mode=network)
        self.container = self.client.create_container(image_name, name='nwnee_' + str(server_cfg['id']),
                                                      stdin_open=True,
                                                      host_config=cfg_host, environment=self._cfg)
        self._socket = None

    def container_status(self):
        inspect_dict = self.client.inspect_container(self.container)
        state = inspect_dict['State']
        if 'Status' in state:
            return state['Status']
        else:
            return 'None'

    def get_active_users(self):
        """
        This method gets and returns the active users
        """
        raw_user_list = self._get_server_cmd('status\n', start_flt='Server Name:', end_flt='----\n')
        serv_status = self.raw_user_list(raw_user_list)

        return serv_status

    def _parse_active_users(self, raw_data):
        """
        This method takes a large bitarray string, finds the user table and parses out all the user information into
        a user structure
        """
        users = list()

        # Split long string into individual lines and put each one in it's own row
        rows_split = raw_data.decode().split('\n')

        # Find rows with the table column delimiter '|' in them
        user_idxs = [i for i, row in enumerate(rows_split) if '|' in row]

        # Remove the column labels from table
        user_idxs.pop(0)

        if len(user_idxs) > 0:

            # go through each row with '|' and split the string into it's columns based on the '|' delimiter and put
            # into final user dictionary
            for user_idx in user_idxs:
                row = rows_split[user_idx].split('|')
                users.append([{'id': row[0].strip(), 'player_name': row[1].strip(), 'ip': row[2].strip(),
                               'char_name': row[3].strip(), 'cd_key': row[4].strip()}])

        return users

    def _get_server_cmd(self, cmd, start_flt, timeout=10, retry_cnt=3):
        """
        This method sends a command to the server and returns all the data starting at the start_flt string to the
        EOF.
        """
        # This sets the retry count
        while retry_cnt > 0:
            start_time = time.time()
            start_flt_b = start_flt.encode()
            data_buf = bytearray()

            # Turn off blocking because there is no communications protocol to know the size of a message ahead of time
            self._socket.setblocking(False)

            # Send several end of line to flush out any previously unhandled commands
            self._socket.send('\n\n'.encode())
            # Give some time for the server to register the command

            # TODO: 1 second is just a best guess, there might be a better way to handle this
            time.sleep(1)
            # Send command to the server
            self._socket.send(cmd.encode())
            # TODO: 1 second is just a best guess, there might be a better way to handle this
            time.sleep(1)

            # Wait for there to be data to read from the socket
            select.select([self._socket], [], [], 5)

            # This is set to True once the start filter string pattern is detected
            received_start_flt = False

            # This is set once recv fails after the string pattern, this *should* represent the EOL.
            # TODO: This is not a very clean implementation but no better implementation is obvious at this time
            pkt_complete = False
            # This will be updated with the start idx of the filter string pattern when it detected
            start_indx = 0

            while True:
                try:
                    # TODO: investigate increasing the recv size to optimize speed
                    data_buf += self._socket.recv(1)
                except:
                    # TODO: This makes the assumption that a recv error after the start filter packet is a EOL.
                    if received_start_flt:
                        pkt_complete = True
                    time.sleep(1)

                # Detect the start of the data of interest based on the start filter string
                if data_buf[-len(start_flt_b):] == start_flt_b:
                    received_start_flt = True
                    start_indx = len(data_buf) - len(start_flt_b)

                # Once there is an EOF after the start filter match then return the data
                if pkt_complete and received_start_flt:
                    data = data_buf[start_indx:]
                    return data

                # In case the start filter string or the EOF is not detected, this provides a timeout.
                if time.time() - start_time > timeout:
                    print('Server send cmd time exceeded timeout time of: ' + str(timeout) + 's')
                    retry_cnt -= 1
                    start_time = time.time()
                    break
        return 0

    def start(self):
        self.client.start(self.container)

        # wait for container to load
        timeout = 10
        while self.container_status() != "running":
            time.sleep(1)
            timeout -= 1
            if timeout == 0:
                print("container timed out")
                break

        tmp_s = self.client.attach_socket(self.container, params={'stdin': 1, 'stream': 1, 'stdout': 1})
        self._socket = tmp_s._sock

    def restart(self):
        self.client.restart(self.container)

    def stop(self):
        self.client.stop(self.container)

    def _load_cfg(self, cfg):
        self._cfg = {
            'NWN_PORT': cfg['port'],
            'NWN_MODULE': cfg['module_name'],
            'NWN_SERVERNAME': cfg['server_name'],
            'NWN_PUBLICSERVER': cfg['public_server'],
            'NWN_MAXCLIENTS': cfg['max_players'],
            'NWN_MINLEVEL': cfg['min_level'],
            'NWN_MAXLEVEL': cfg['max_players'],
            'NWN_PAUSEANDPLAY': cfg['pause_play'],
            'NWN_PVP': cfg['pvp'],
            'NWN_SERVERVAULT': cfg['server_vault'],
            'NWN_ELC': cfg['enforce_legal_char'],
            'NWN_ILR': cfg['item_lv_restrictions'],
            'NWN_GAMETYPE': cfg['game_type'],
            'NWN_ONEPARTY': cfg['one_party'],
            'NWN_DIFFICULTY': cfg['difficulty'],
            'NWN_AUTOSAVEINTERVAL': cfg['auto_save_interval'],
            'NWN_RELOADWHENEMPTY': cfg['reload_when_empty'],
            'NWN_PLAYERPASSWORD': cfg['player_pwd'],
            'NWN_DMPASSWORD': cfg['dm_pwd'],
            'NWN_ADMINPASSWORD': cfg['admin_pwd']
        }
        # unused NWN environment variables:
        #    NWN_NWSYNCURL
        #    NWN_NWSYNCHASH


import docker
import time
import db

# TODO: It might make sense to remove all the low level string manipulation/extraction methods into their own class
# TODO: Look into better structuring the __init__. Should the client be passed to the constructor or created inside?
# TODO: Think through how start() should handle if a container exists or is already running.


class NwnServer:
    def __init__(self, server_cfg, docker_name, image_name='nwnxee/unified', network='host'):
        self._load_nwn_cfg(server_cfg)
        self.client = docker.APIClient()
        self._socket = None
        self.image_name = image_name
        self.network = network
        self.docker_name = docker_name
        self.container = None
        self.server_cfg_id = server_cfg['id']
        self.server_cfg = server_cfg

    def get_server_name(self):
        return self.server_cfg['server_name']

    def remove_container(self):
        nwn_containers = self.client.containers(all=True, filters={"name": self.docker_name})
        if len(nwn_containers) > 0:
            container = nwn_containers[0]
            inspect_dict = self.client.inspect_container(container)
            state = inspect_dict['State']

            # Remove old container before creating new one
            if 'Status' in state:
                if state['Status'] == 'running':
                    self.client.stop(container)
                self.client.remove_container(container)

    def create_container(self):
        # Remove any old copies of the container
        self.remove_container()
        volumes = db.get_volumes(self.server_cfg_id)
        cfg_host = self.client.create_host_config(network_mode=self.network, binds=volumes)

        self.container = self.client.create_container(self.image_name,
                                                      name=self.docker_name,
                                                      stdin_open=True,
                                                      host_config=cfg_host, environment=self._cfg)

    def container_status(self):
        # TODO: Look into setting parameters in DB as boolean instead of int.
        if self.server_cfg['is_active'] == 0:
            return 'Not Activated'

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

        raw_user_list = self._get_server_cmd('status\n', start_flt='Server Name:')

        try:
            if len(raw_user_list):
                active_users = self._parse_active_users(raw_user_list)
            else:
                active_users = {}

            return active_users
        except:
            i = 1+1

    def _parse_active_users(self, raw_data):
        """
        This method takes a large bitarray string, finds the user table and parses out all the user information into
        a user structure
        """
        users = dict()

        # Split long string into individual lines and put each one in it's own row
        user_idxs = []
        try:
            rows_split = raw_data.decode().split('\n')
            # Find rows with the table column delimiter '|' in them
            user_idxs = [i for i, row in enumerate(rows_split) if '|' in row]

            # Remove the column labels from table
            user_idxs.pop(0)

        except:
            print("bad decode!")

        if len(user_idxs) > 0:

            # go through each row with '|' and split the string into it's columns based on the '|' delimiter and put
            # into final user dictionary
            for user_idx in user_idxs:
                row = rows_split[user_idx].split('|')

                if len(row) == 5:
                    users[row[4].strip()] = {'id': row[0].strip(), 'player_name': row[1].strip(), 'ip_addr': row[2].strip(),
                                             'character_name': row[3].strip(), 'docker_name': self.docker_name,
                                             'server_name': self.server_cfg['server_name']}

        return users

    def _get_server_cmd(self, cmd, start_flt, timeout=3, retry_cnt=3):
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

            # Send command to the server
            self._socket.send(cmd.encode())

            while True:
                try:
                    # TODO: investigate increasing the recv size to optimize speed
                    data_buf += self._socket.recv(1048)
                except:
                    # TODO: This makes the assumption that a recv error after the start filter packet is a EOL.
                    if start_flt_b in data_buf:
                        start_index = data_buf.find(start_flt_b)
                        return data_buf[start_index:]

                # In case the start filter string or the EOF is not detected, this provides a timeout.
                if time.time() - start_time > timeout:
                    print(f"cmd time exceeded timeout time of: {timeout}s with retries {retry_cnt} remaining")
                    retry_cnt -= 1
                    start_time = time.time()
                    break
        return []

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

    def _load_nwn_cfg(self, cfg):
        # See https://nwnxee.github.io/unified/group__nwnx.html
        self._cfg = {
            'NWN_PORT': cfg['port'],
            'NWN_MODULE': cfg['module_name'],
            'NWN_SERVERNAME': cfg['server_name'],
            'NWN_PUBLICSERVER': cfg['public_server'],
            'NWN_MAXCLIENTS': cfg['max_players'],
            'NWN_MINLEVEL': cfg['min_level'],
            'NWN_MAXLEVEL': cfg['max_level'],
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
        # TODO: This is a temporary hack for DB support a full configuration interface will be added later
        if cfg['database'] == 'yes':
            self._cfg['NWNX_CORE_SKIP_ALL'] = 'y'
            self._cfg['NWNX_SQL_SKIP'] = 'n'
            self._cfg['NWNX_SQL_DATABASE'] = "nwn"
            self._cfg['NWNX_SQL_PASSWORD'] = "atbp1994"
            self._cfg['NWNX_SQL_USERNAME'] = "nwn"
            self._cfg['NWNX_SQL_HOST'] = "172.17.0.1"
            self._cfg['NWNX_SQL_PORT'] = "3306"
            self._cfg['NWNX_SQL_TYPE'] = "MYSQL"




        # unused NWN environment variables:
        #    NWN_NWSYNCURL
        #    NWN_NWSYNCHASH

"""
Character Service - Provides reusable character data access from BIC files.

This service allows fetching character sheet data from servervault directories
across the application.
"""

import os
from ..extensions import db
from ..models.server_nwn import ServerConfigs, ServerVolumes, VolumesDirs
from ..tools.nwn_editors.character_editor import Character


class CharacterService:
    """Service for reading character data from BIC files."""

    @staticmethod
    def get_servervault_path(server_name):
        """
        Get the servervault directory path for a given server.

        Args:
            server_name (str): Name of the server

        Returns:
            str: Path to servervault directory, or None if not found
        """
        # Get server config by name
        server_config = db.session.query(ServerConfigs).filter_by(server_name=server_name).first()

        if not server_config:
            return None

        # Get all volume mappings for this server
        server_volumes = db.session.query(ServerVolumes).filter_by(
            server_configs_id=server_config.id
        ).all()

        if not server_volumes:
            return None

        # Extract volume_info_ids
        volume_ids = [sv.volumes_info_id for sv in server_volumes]

        # Find the servervault mount
        servervault = db.session.query(VolumesDirs).filter(
            VolumesDirs.volumes_info_id.in_(volume_ids),
            VolumesDirs.dir_mount_loc == '/nwn/home/servervault'
        ).first()

        if servervault:
            return servervault.dir_src_loc

        return None

    @staticmethod
    def load_character_data(cd_key, character_name, server_name, fields=None):
        """
        Load character data from a BIC file.

        Args:
            cd_key (str): Character's CD key (directory name in servervault)
            character_name (str): Character's name (BIC filename without .bic extension)
            server_name (str): Name of the server
            fields (list, optional): List of field names to extract.
                                    If None, returns common fields.

        Returns:
            dict: Dictionary containing requested character data, or None if file not found

        Common fields:
            - ClassLevel: Character level
            - FirstName: Character's first name
            - LastName: Character's last name (may not exist)
            - Class: Class ID
            - Race: Race ID
            - Experience: Total XP
            - HitPoints: Current HP
            - MaxHitPoints: Maximum HP
            - Gold: Gold amount
            - Str, Dex, Con, Int, Wis, Cha: Ability scores
            - Description: Character description
            - Portrait: Portrait filename
        """
        # Player has not selected a character yet
        if character_name.lower() == 'no character':
            return None

        # Default fields if none specified
        if fields is None:
            fields = [
                'ClassLevel', 'FirstName', 'LastName', 'Class', 'Race',
                'Experience', 'HitPoints', 'MaxHitPoints', 'Gold'
            ]

        # Get servervault path
        servervault_path = CharacterService.get_servervault_path(server_name)

        if not servervault_path:
            return None

        # Convert character name to filename format: lowercase and remove spaces
        filename = character_name.lower().replace(' ', '')

        # Construct full path to character file: servervault/CD_KEY/charactername.bic
        char_file = os.path.join(servervault_path, cd_key, f"{filename}.bic")

        if not os.path.exists(char_file):
            return None

        # Load character
        try:
            char = Character()
            char.load_file(char_file)

            # Extract requested fields
            result = {'cd_key': cd_key}

            for field_name in fields:
                if field_name == 'ClassLevel':
                    # npc_data only keeps the first class entry; sum across all classes
                    class_level_idx = next(
                        (i for i, lbl in enumerate(char.labels) if lbl == 'ClassLevel'),
                        None
                    )
                    if class_level_idx is not None:
                        result['ClassLevel'] = sum(
                            f.data_or_offset for f in char.fields
                            if f.label_index == class_level_idx
                        ) or None
                    else:
                        result['ClassLevel'] = None
                elif field_name in char.npc_data:
                    result[field_name] = char.npc_data[field_name].value
                else:
                    result[field_name] = None

            return result

        except Exception as e:
            # Log error but don't crash
            print(f"Error loading character {cd_key} from {server_name}: {e}")
            return None

    @staticmethod
    def get_character_level(cd_key, character_name, server_name):
        """
        Get the total character level (sum of all class levels).

        Args:
            cd_key (str): Character's CD key
            character_name (str): Character's name
            server_name (str): Name of the server

        Returns:
            int: Total character level, or None if not found
        """
        data = CharacterService.load_character_data(cd_key, character_name, server_name, fields=['ClassLevel'])
        if data and 'ClassLevel' in data:
            return data['ClassLevel']
        return None

    @staticmethod
    def get_character_summary(cd_key, character_name, server_name):
        """
        Get a summary of character information suitable for display lists.

        Args:
            cd_key (str): Character's CD key
            character_name (str): Character's name
            server_name (str): Name of the server

        Returns:
            dict: Character summary with level, name, class, and race
        """
        fields = ['ClassLevel', 'FirstName', 'LastName', 'Class', 'Race']
        data = CharacterService.load_character_data(cd_key, character_name, server_name, fields=fields)

        if data:
            # Format full name
            full_name = data.get('FirstName', '')
            if data.get('LastName'):
                full_name += f" {data['LastName']}"
            data['full_name'] = full_name

        return data

from flask import url_for
from ..models.server_nwn import ServerConfigs, ServerVolumes, VolumesDirs
from ..services.character_service import CharacterService
import os


def get_vault_url(server_name, cd_key):
    """
    Generate a URL to view a character's vault folder in the volume manager.
    
    Args:
        server_name (str): Name of the server
        cd_key (str): Character's CD key
    
    Returns:
        str: URL to the volume editor page, or None if not found
    """
    servervault_path = CharacterService.get_servervault_path(server_name)
    if not servervault_path:
        return None
    
    try:
        server_config = ServerConfigs.query.filter_by(server_name=server_name).first()
        if not server_config:
            return None
            
        server_volumes = ServerVolumes.query.filter_by(server_configs_id=server_config.id).all()
        if not server_volumes:
            return None
            
        volume_ids = [sv.volumes_info_id for sv in server_volumes]
        servervault_mount = VolumesDirs.query.filter(
            VolumesDirs.volumes_info_id.in_(volume_ids),
            VolumesDirs.dir_mount_loc == '/nwn/home/servervault',
            VolumesDirs.dir_src_loc == servervault_path
        ).first()
        
        if not servervault_mount:
            return None
            
        full_path = os.path.join(servervault_path, cd_key)
        return url_for('volume_manager.edit', id=servervault_mount.volumes_info_id, path=full_path)
        
    except Exception as e:
        print(f"Error generating vault URL: {e}")
        return None

# GS manager
This is the source code for an open-source project for managing NeverWinter Nights game servers using docker. All testing to date has been done using Linux, this should also work on Windows but there might be some bugs. Here are the following key features of this project
* Currently supported features
  * Create and run multiple game servers each with its own config
  * Create groups of volumes that can be used by one or many game servers
  * Easily manage CEP packs
  * Manage databases used for persistant worlds
  * View actively logged in players
  * Very basic character editor (not stable)
  * Restful API
* Features under development
  * Support for emailing/texting distribution lists when players log on
    * Will be configurable and will allow for distribution lists
  * Pulling of specific NWN docker versions and updating to latest
  * Selecting different docker images other than nwn
  * Full featured vharacter editor
  * Log file viewer
  * Unit tests
* Features considered but not yet planned
  * Revamp integrated file manager to be more modern
  * Support for managing other game servers
  * Support for managing/running nwn servers outside of docker 
  
## Installation
* Under construction
## Screenshots
### Server Management
#### List/Control active servers
![List Servers](https://github.com/svolpe/gs-manager/blob/main/docs/screenshots/servers.png)
#### Add new server
![Server Config 1](https://github.com/svolpe/gs-manager/blob/main/docs/screenshots/server_config_1.png)
![Server Config 2](https://github.com/svolpe/gs-manager/blob/main/docs/screenshots/server_config_3.png)
![Server Config 3](https://github.com/svolpe/gs-manager/blob/main/docs/screenshots/server_config_2.png)
* The **volumes** selection allows you to select what docker volume mounts from the volume manager that you want available for this server. Volumes can also be overlaid.
#### Volume management
#### List/Add/Delete Volumes
![List Volumes](https://github.com/svolpe/gs-manager/blob/main/docs/screenshots/volume_manager.png)
#### Enter Volume Information
![List Volumes Edit](https://github.com/svolpe/gs-manager/blob/main/docs/screenshots/volume_manager_edit.png)
#### Integrated File Manager: Upload/download/delete modules and characters including a character editor
You can browser up and down directories by clicking on the links and the ".." lets you go back a directory. The max top level is set in a server config file to protect against accessing other portions of your server
##### Server Modules
![Manager Server Modules](https://github.com/svolpe/gs-manager/blob/main/docs/screenshots/file_manager_module.png)
##### Characters
##### Character Editor
![Character Editor](https://github.com/svolpe/gs-manager/blob/main/docs/screenshots/file_manager_character_editor.png)

![Manager Server Modules](https://github.com/svolpe/gs-manager/blob/main/docs/screenshots/file_manager_character.png)
#### Logged in Users
![List Users](https://github.com/svolpe/gs-manager/blob/main/docs/screenshots/players.png)


# GS manager
This is the source code for an open-source project for managing NeverWinter Nights game servers using docker. Here are the following key features of this project
* Create and run multiple game servers each with its own config
* Create groups of volumes that can be used by one or many game servers
* Easily manage CEP packs
* Manage databases used for persistant worlds
* View actively logged in players
* Use google drive to actively back up configurations, character and module vaults (under development)
## Installation
* Under construction


## Testing
### Locking sqlite using command line:

* Lock db
```
PRAGMA locking_mode = EXCLUSIVE;
BEGIN EXCLUSIVE;
SELECT * FROM pc_active_log LIMIT 1;
COMMIT;
```
* Unlock db
```
PRAGMA locking_mode = NORMAL; 
SELECT * FROM pc_active_log LIMIT 1;
```
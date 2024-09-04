from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os


# TODO: Move this into some sort of config file or database
PATH_STORAGE = '/home/v_malarik/dev/gs-manager/instance/docker_storage'

db = SQLAlchemy()
migrate = Migrate()

def change_dir_safe(new_dir):
#    chg_dir = copy(new_dir)

    #TODO: The following change directory code is very ugly, look at refactoring...
    shared_prefix = os.path.commonprefix([new_dir, PATH_STORAGE])
    if shared_prefix != PATH_STORAGE:
        #Return to safe location
        new_dir = PATH_STORAGE 
    
    os.chdir(new_dir)
    return new_dir

def db_upsert(queries, model):
    for each in model.query.filter(model.id.in_(queries.keys())).all():
        # Only merge those posts which already exist in the database
        db.session.merge(queries.pop(each.id))

    # Only add those posts which did not exist in the database
    db.session.add_all(queries.values())

    # Now we commit our modifications (merges) and inserts (adds) to the database!
    db.session.commit()

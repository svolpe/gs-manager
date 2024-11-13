from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os


db = SQLAlchemy()
migrate = Migrate()


def clone_model(model, **kwargs):
    """Clone an arbitrary sqlalchemy model object without its primary key values."""
    # Ensure the model’s data is loaded before copying.
    model.id

    table = model.__table__
    non_pk_columns = [k for k in table.columns.keys() if k not in table.primary_key.columns.keys()]
    data = {c: getattr(model, c) for c in non_pk_columns}
    data.update(kwargs)

    clone = model.__class__(**data)
    db.session.add(clone)
    db.session.commit()
    return clone


def change_dir_safe(new_dir, path_storage):
    # TODO: The following change directory code is very ugly, look at refactoring...
    shared_prefix = os.path.commonprefix([new_dir, path_storage])
    if shared_prefix != path_storage:
        new_dir = path_storage
    
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

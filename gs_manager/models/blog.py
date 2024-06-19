from ..extensions import db
from sqlalchemy import (ForeignKey, func)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    author_id = db.Column(db.Integer, unique=False, nullable=False, )
    created = db.Column(db.TIMESTAMP(timezone=True), server_default=func.now())
    title = db.Column(db.String(80), unique=False, nullable=False)
    body = db.Column(db.String, unique=False, nullable=False)
    db.column('author_id', ForeignKey("User.id"))

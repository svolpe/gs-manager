from ..extensions import db
from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash


class User(UserMixin, db.Model):
    """
    Class that represents a user of the application

    The following attributes of a user are stored in this table:
        * user name - User ID/Name for user
        * password - hashed password (using werkzeug.security)
        * registered_on - date & time that the user registered

    REMEMBER: Never store the plaintext password in a database!
    """

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_name = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    registered_on = mapped_column(DateTime(), nullable=False)
    
    def __init__(self, user_name: str, password_plaintext: str):
        """Create a new User object using the user name and hashing the
        plaintext password using Werkzeug.Security.
        """
        self.user_name = user_name
        self.password = self._generate_password_hash(password_plaintext)
        self.registered_on = datetime.now()

    def is_password_correct(self, password_plaintext: str):
        return check_password_hash(self.password, password_plaintext)

    def set_password(self, password_plaintext: str):
        self.password = self._generate_password_hash(password_plaintext)

    @staticmethod
    def _generate_password_hash(password_plaintext):
        return generate_password_hash(password_plaintext)

    def __repr__(self):
        return f'<User: {self.user_name}>'

    

import os
import uuid
from datetime import datetime
from sqlalchemy.orm import deferred
from sqlalchemy import UUID, text, inspect
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()


#-----------------------------------   ACCOUNTS   -----------------------------------
class people(db.Model, UserMixin):
    id = db.Column(db.UUID, unique=True, primary_key=True, default=db.func.gen_random_uuid())
    name = db.Column(db.String(30), nullable=False)
    surname = db.Column(db.String(30), nullable=False)
    lastname = db.Column(db.String(30))
    group_number = db.Column(db.Integer, nullable=True)
    group_letter = db.Column(db.String(2), nullable=True)
    phone = db.Column(db.String(30), nullable=True, unique=True)
    campus = db.Column(db.String(20), default='khodynka')  # khodynka, kaplya
    total_score = db.Column(db.Integer, default=0, nullable=False)
    password_hash = db.Column(db.String(128), nullable=True)
    apartment = db.Column(db.String(10), nullable=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        if not self.password_hash:
            return False
        return bcrypt.check_password_hash(self.password_hash, password)

    def get_id(self):
        return f"student-{self.id}"

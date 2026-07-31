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


#-----------------------------------   SERVICE REQUESTS   -----------------------------------
class ServiceRequest(db.Model):
    id = db.Column(db.UUID, unique=True, primary_key=True, default=db.func.gen_random_uuid())
    user_id = db.Column(db.UUID, db.ForeignKey('people.id'), nullable=True)
    number = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(60), nullable=False)
    description = db.Column(db.Text, nullable=False)
    apartment = db.Column(db.String(10), nullable=True)
    entrance = db.Column(db.String(10), nullable=True)
    urgency = db.Column(db.String(10), default='normal', nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    status = db.Column(db.String(20), default='new', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)


#-----------------------------------   GUEST PASSES   -----------------------------------
class GuestPass(db.Model):
    id = db.Column(db.UUID, unique=True, primary_key=True, default=db.func.gen_random_uuid())
    user_id = db.Column(db.UUID, db.ForeignKey('people.id'), nullable=True)
    number = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(30), nullable=False)        # guest, courier, delivery, transport, permanent
    transport = db.Column(db.String(20), nullable=True)        # walking, car, taxi, cargo
    visit_at = db.Column(db.DateTime, nullable=True)           # когда приедет
    guest_name = db.Column(db.String(120), nullable=True)      # имя гостя
    guest_phone = db.Column(db.String(30), nullable=True)      # телефон гостя
    status = db.Column(db.String(20), default='new', nullable=False)
    arrived_at = db.Column(db.DateTime, nullable=True)         # когда гость сообщил о прибытии
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)


#-----------------------------------   WEBAUTHN / BIOMETRICS   -----------------------------------
class WebAuthnCredential(db.Model):
    __tablename__ = 'webauthn_credential'
    id = db.Column(db.UUID, unique=True, primary_key=True, default=db.func.gen_random_uuid())
    user_id = db.Column(db.UUID, db.ForeignKey('people.id'), nullable=False, index=True)
    credential_id = db.Column(db.String(512), nullable=False, unique=True)
    public_key = db.Column(db.Text, nullable=False)
    transports = db.Column(db.String(120), nullable=True)
    label = db.Column(db.String(120), nullable=True)
    sign_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)


#-----------------------------------   NOTIFICATIONS   -----------------------------------
class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.UUID, unique=True, primary_key=True, default=db.func.gen_random_uuid())
    user_id = db.Column(db.UUID, db.ForeignKey('people.id'), nullable=False, index=True)
    type = db.Column(db.String(30), nullable=False)            # guest_arrived, request, system
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.Text, nullable=True)
    pass_id = db.Column(db.UUID, nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

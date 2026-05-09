from database import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(255))
    google_id = db.Column(db.String(255))
    phone = db.Column(db.String(15))
    is_active = db.Column(db.Boolean, default=True)
    role = db.Column(db.Enum('ADMIN', 'CUSTOMER'), default='CUSTOMER')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

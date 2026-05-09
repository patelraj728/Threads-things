from database import db
from datetime import datetime


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # address snapshot
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(15))
    address_line = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(10))

    total_amount = db.Column(db.Numeric(10, 2))

    status = db.Column(db.Enum(
        'PLACED',
        'CONFIRMED',
        'PACKED',
        'SHIPPED',
        'OUT_FOR_DELIVERY',
        'DELIVERED',
        'CANCELLED'
    ), default='PLACED')

    payment_status = db.Column(db.Enum('PENDING', 'PAID', 'FAILED'), default='PENDING')

    tracking_id = db.Column(db.String(100))
    courier_name = db.Column(db.String(100))
    custom_message = db.Column(db.Text, nullable=True)   # FIX: customer custom order message
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('orders', lazy=True))

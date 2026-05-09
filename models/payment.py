from database import db
from datetime import datetime

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))

    payment_method = db.Column(db.Enum('COD', 'ONLINE'))
    transaction_id = db.Column(db.String(255))
    status = db.Column(db.Enum('SUCCESS', 'PENDING', 'FAILED'))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    order = db.relationship('Order', backref=db.backref('payment', uselist=False))

from database import db
from datetime import datetime

class Wishlist(db.Model):
    __tablename__ = 'wishlist'
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id'),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('wishlist_items', lazy=True))
    product = db.relationship('Product')

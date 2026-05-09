from database import db

class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))

    quantity = db.Column(db.Integer)
    price = db.Column(db.Numeric(10, 2))

    custom_text = db.Column(db.String(255))
    custom_notes = db.Column(db.Text)

    order = db.relationship('Order', backref=db.backref('items', cascade='all, delete', lazy=True))
    product = db.relationship('Product')

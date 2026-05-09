from database import db

class Cart(db.Model):
    __tablename__ = 'cart'
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id'),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    quantity = db.Column(db.Integer)

    user = db.relationship('User', backref=db.backref('cart_items', lazy=True))
    product = db.relationship('Product')

    @property
    def subtotal(self):
        return float(self.product.price) * self.quantity
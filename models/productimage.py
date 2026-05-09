from database import db

class ProductImage(db.Model):
    __tablename__ = 'product_images'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'))
    image_url = db.Column(db.Text)

    product = db.relationship('Product', backref=db.backref('images', cascade='all, delete', lazy=True))

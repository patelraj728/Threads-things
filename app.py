from flask import Flask, redirect, url_for, render_template, request,session
from database import db
from models.product import Product
from models.category import Category
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.wishlist import wishlist_bp
from routes.product import product_bp
from routes.cart import cart_bp
from routes.order import order_bp        # FIX: was missing
from routes.profile import profile_bp
from routes.chat import chat_bp
from models.cart import Cart
from models.wishlist import Wishlist    # FIX: was missing
from dotenv import load_dotenv           # FIX: use .env file
import os

load_dotenv()  # FIX: loads .env variables


def create_app():
    app = Flask(__name__)

    # FIX: All secrets from environment variables, never hardcoded
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['UPLOAD_FOLDER'] = 'static/uploads'

    db.init_app(app)

    # FIX: All blueprints registered
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(wishlist_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(order_bp)     # FIX: added
    app.register_blueprint(profile_bp)   # FIX: added
    app.register_blueprint(chat_bp)

    @app.route('/')
    def index():
        category_id = request.args.get('category', type=int)  # FIX: category filter
        categories = Category.query.all()
        if category_id:
            products = Product.query.filter_by(category_id=category_id, is_active=True).all()
        else:
            products = Product.query.filter_by(is_active=True).limit(8)
        return render_template('index.html', products=products, categories=categories, selected_category=category_id)
    return app


app = create_app()
@app.context_processor
def inject_counts():

    cart_count = 0
    wishlist_count = 0

    if session.get('user_id'):

        cart_count = db.session.query(
            db.func.sum(Cart.quantity)
        ).filter_by(
            user_id=session['user_id']
        ).scalar() or 0

        wishlist_count = Wishlist.query.filter_by(
            user_id=session['user_id']
        ).count()

    return dict(
        cart_count=cart_count,
        wishlist_count=wishlist_count
    )
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from models.product import Product
from models.review import Review
from models.order import Order
from models.category import Category
from models.orderitem import OrderItem
from database import db
from decorators import login_required
from sqlalchemy import or_

product_bp = Blueprint('product', __name__, url_prefix='/product')

@product_bp.route('/shop', methods=['GET'])
def shop():
    # ── Read query params ─────────────────────────────────────────────
    category_id = request.args.get('category', type=int)
    search_q    = (request.args.get('q') or '').strip()
    min_price   = request.args.get('min_price', type=float)
    max_price   = request.args.get('max_price', type=float)
    sort        = (request.args.get('sort') or 'newest').strip()

    # ── Build query ───────────────────────────────────────────────────
    query = Product.query.filter_by(is_active=True)

    if category_id:
        query = query.filter(Product.category_id == category_id)

    if search_q:
        like = f"%{search_q}%"
        # Search by name OR description (description is optional in most schemas)
        if hasattr(Product, 'description'):
            query = query.filter(or_(Product.name.ilike(like),
                                     Product.description.ilike(like)))
        else:
            query = query.filter(Product.name.ilike(like))

    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    # ── Sorting ───────────────────────────────────────────────────────
    if sort == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort == 'name_asc':
        query = query.order_by(Product.name.asc())
    elif sort == 'name_desc':
        query = query.order_by(Product.name.desc())
    else:  # 'newest' (default)
        if hasattr(Product, 'created_at'):
            query = query.order_by(Product.created_at.desc())
        else:
            query = query.order_by(Product.id.desc())

    products   = query.all()
    categories = Category.query.all()

    return render_template(
        'shop.html',
        products=products,
        categories=categories,
        selected_category=category_id,
        search_q=search_q,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
    )



@product_bp.route('/<int:product_id>', methods=['GET'])
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)   # FIX: was get() which returns None silently
    reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_at.desc()).all()
    other_product = Product.query.filter_by(category_id=product.category_id).limit(4)
    # other_product = Product.query.filter_by(category_id=product)
    # check if logged-in user can leave a review (must have bought and not reviewed yet)
    can_review = False
    already_reviewed = False
    if session.get('user_id'):
        already_reviewed = Review.query.filter_by(
            user_id=session['user_id'], product_id=product_id
        ).first() is not None

        if not already_reviewed:
            # check if user bought this product and order is DELIVERED
            bought = db.session.query(OrderItem).join(Order).filter(
                Order.user_id == session['user_id'],
                OrderItem.product_id == product_id,
                Order.status == 'DELIVERED'
            ).first()
            can_review = bought is not None

    avg_rating = None
    if reviews:
        avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1)

    return render_template(
        'product_detail.html',
        product=product,
        reviews=reviews,
        can_review=can_review,
        already_reviewed=already_reviewed,
        avg_rating=avg_rating,
        other_products=other_product
    )


@product_bp.route('/<int:product_id>/review', methods=['POST'])
@login_required
def add_review(product_id):
    Product.query.get_or_404(product_id)

    # verify purchase
    bought = db.session.query(OrderItem).join(Order).filter(
        Order.user_id == session['user_id'],
        OrderItem.product_id == product_id,
        Order.status == 'DELIVERED'
    ).first()

    if not bought:
        flash('You can only review products you have purchased.', 'error')
        return redirect(url_for('product.product_detail', product_id=product_id))

    existing = Review.query.filter_by(user_id=session['user_id'], product_id=product_id).first()
    if existing:
        flash('You have already reviewed this product.', 'error')
        return redirect(url_for('product.product_detail', product_id=product_id))

    rating = int(request.form.get('rating', 5))
    comment = request.form.get('comment', '').strip()

    if not 1 <= rating <= 5:
        flash('Rating must be between 1 and 5.', 'error')
        return redirect(url_for('product.product_detail', product_id=product_id))

    review = Review(
        user_id=session['user_id'],
        product_id=product_id,
        rating=rating,
        comment=comment
    )
    db.session.add(review)
    db.session.commit()
    flash('Review submitted!', 'success')
    return redirect(url_for('product.product_detail', product_id=product_id))



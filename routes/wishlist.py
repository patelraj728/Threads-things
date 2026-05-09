from flask import Blueprint, render_template, redirect, session, url_for, flash, request, jsonify
from database import db
from models.wishlist import Wishlist
from decorators import login_required

wishlist_bp = Blueprint('wishlist', __name__, url_prefix='/wishlist')


def _is_ajax():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


@wishlist_bp.route('/', methods=['GET'])
@login_required
def wishlist():
    wishlist_items = Wishlist.query.filter_by(user_id=session['user_id']).all()
    return render_template('wishlist.html', wishlist_items=wishlist_items)


@wishlist_bp.route('/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_wishlist(product_id):
    existing = Wishlist.query.filter_by(
        user_id=session['user_id'], product_id=product_id
    ).first()

    if existing:
        if _is_ajax():
            return jsonify({'ok': True, 'already': True})
        flash('Already in your wishlist.', 'info')
        return redirect(url_for('index'))

    db.session.add(Wishlist(user_id=session['user_id'], product_id=product_id))
    db.session.commit()
    if _is_ajax():
        wishlist_count = Wishlist.query.filter_by(
        user_id=session['user_id']
        ).count()

        return jsonify({
            'ok': True,
            'wishlist_count': wishlist_count
        })
    flash('Added to wishlist!', 'success')
    return redirect(url_for('wishlist.wishlist'))


@wishlist_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_wishlist_item(id):
    item = Wishlist.query.get_or_404(id)
    if item.user_id != session['user_id']:
        if _is_ajax():
            return jsonify({'ok': False}), 403
        flash('Unauthorized.', 'error')
        return redirect(url_for('wishlist.wishlist'))
    db.session.delete(item)
    db.session.commit()
    if _is_ajax():
        return jsonify({'ok': True})
    return redirect(url_for('wishlist.wishlist'))


@wishlist_bp.route('/move-to-cart/<int:id>', methods=['POST'])
@login_required
def move_to_cart(id):
    from models.cart import Cart
    item = Wishlist.query.get_or_404(id)
    if item.user_id != session['user_id']:
        if _is_ajax():
            return jsonify({'ok': False}), 403
        flash('Unauthorized.', 'error')
        return redirect(url_for('wishlist.wishlist'))

    existing = Cart.query.filter_by(user_id=session['user_id'], product_id=item.product_id).first()
    if not existing:
        db.session.add(Cart(user_id=session['user_id'], product_id=item.product_id, quantity=1))

    db.session.delete(item)
    db.session.commit()
    if _is_ajax():
        return jsonify({'ok': True})
    flash('Moved to cart!', 'success')
    return redirect(url_for('cart.cart'))

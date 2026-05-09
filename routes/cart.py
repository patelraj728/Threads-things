from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models.product import Product
from models.cart import Cart
from database import db
from decorators import login_required

cart_bp = Blueprint('cart', __name__, url_prefix='/cart')


def _is_ajax():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


@cart_bp.route('/', methods=['GET'])
@login_required
def cart():
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    total = sum(item.subtotal for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)


@cart_bp.route('/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))

    if product.stock_quantity < 1:
        if _is_ajax():
            return jsonify({'ok': False, 'error': 'out_of_stock'}), 400
        flash('This product is out of stock.', 'error')
        return redirect(url_for('product.product_detail', product_id=product_id))

    existing = Cart.query.filter_by(
        user_id=session['user_id'], product_id=product_id
    ).first()

    if existing:
        existing.quantity = min(existing.quantity + quantity, product.stock_quantity)
    else:
        db.session.add(Cart(user_id=session['user_id'], product_id=product_id, quantity=quantity))

    db.session.commit()
    if _is_ajax():
        cart_count = db.session.query(
        db.func.sum(Cart.quantity)
        ).filter_by(
        user_id=session['user_id']
        ).scalar() or 0

        return jsonify({
            'ok': True,
            'message': f'{product.name} added to cart.',
            'cart_count': cart_count
        })
    flash(f'"{product.name}" added to cart.', 'success')
    return redirect(url_for('cart.cart'))


@cart_bp.route('/update/<int:product_id>', methods=['POST'])
@login_required
def update_cart_item(product_id):
    product = Product.query.get_or_404(product_id)
    action = request.form.get('action')

    existing = Cart.query.filter_by(
        user_id=session['user_id'], product_id=product_id
    ).first()

    removed = False
    if existing:
        if action == 'plus':
            if existing.quantity < product.stock_quantity:
                existing.quantity += 1
            elif _is_ajax():
                return jsonify({'ok': False, 'error': 'max_stock',
                                'quantity': existing.quantity,
                                'subtotal': float(existing.subtotal)}), 400
            else:
                flash('Cannot exceed available stock.', 'error')
        elif action == 'minus':
            existing.quantity -= 1
            if existing.quantity <= 0:
                db.session.delete(existing)
                removed = True

    db.session.commit()

    if _is_ajax():
        if removed:
            return jsonify({'ok': True, 'removed': True})
        return jsonify({
            'ok': True,
            'removed': False,
            'quantity': existing.quantity,
            'subtotal': float(existing.subtotal),
        })
    return redirect(url_for('cart.cart'))


@cart_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_cart_item(id):
    cart_item = Cart.query.get_or_404(id)
    if cart_item.user_id != session['user_id']:
        if _is_ajax():
            return jsonify({'ok': False, 'error': 'unauthorized'}), 403
        flash('Unauthorized.', 'error')
        return redirect(url_for('cart.cart'))
    db.session.delete(cart_item)
    db.session.commit()
    if _is_ajax():
        return jsonify({'ok': True, 'removed': True})
    return redirect(url_for('cart.cart'))

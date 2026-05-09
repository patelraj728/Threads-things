from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import db
from models.cart import Cart
from models.order import Order
from models.orderitem import OrderItem
from models.payment import Payment
from models.product import Product
from models.address import Address
from decorators import login_required, admin_required
import os
import razorpay

order_bp = Blueprint('order', __name__, url_prefix='/order')

# =========================================================
# RAZORPAY KEYS
# =========================================================

RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')

# =========================================================
# HELPER
# =========================================================

def _make_buy_now_item(product, quantity):

    return type('BuyNowItem', (), {
        'product_id': product.id,
        'product': product,
        'quantity': quantity,
        'subtotal': product.price * quantity,
    })()

# =========================================================
# CHECKOUT PAGE
# =========================================================

@order_bp.route('/checkout', methods=['GET'])
@login_required
def checkout():

    buy_now_pid = request.args.get('buy_now', type=int)
    buy_now_qty = request.args.get('quantity', default=1, type=int)

    if buy_now_pid:

        product = Product.query.get_or_404(buy_now_pid)

        if buy_now_qty < 1:
            buy_now_qty = 1

        if product.stock_quantity < buy_now_qty:

            flash(
                f'"{product.name}" only has {product.stock_quantity} units available.',
                'error'
            )

            return redirect(
                url_for(
                    'product.detail',
                    product_id=product.id
                )
            )

        cart_items = [
            _make_buy_now_item(product, buy_now_qty)
        ]

        session['buy_now'] = {
            'product_id': product.id,
            'quantity': buy_now_qty
        }

    else:

        session.pop('buy_now', None)

        cart_items = Cart.query.filter_by(
            user_id=session['user_id']
        ).all()

        if not cart_items:

            flash('Your cart is empty.', 'error')

            return redirect(url_for('cart.cart'))

    total = sum(item.subtotal for item in cart_items)

    addresses = Address.query.filter_by(
        user_id=session['user_id']
    ).all()

    return render_template(
        'checkout.html',
        cart_items=cart_items,
        total=total,
        addresses=addresses
    )

# =========================================================
# PLACE ORDER
# =========================================================

@order_bp.route('/place', methods=['POST'])
@login_required
def place_order():

    buy_now = session.get('buy_now')

    # =====================================================
    # GET CART ITEMS
    # =====================================================

    if buy_now:

        product = Product.query.get_or_404(
            buy_now['product_id']
        )

        cart_items = [
            _make_buy_now_item(
                product,
                buy_now['quantity']
            )
        ]

    else:

        cart_items = Cart.query.filter_by(
            user_id=session['user_id']
        ).all()

        if not cart_items:

            flash('Your cart is empty.', 'error')

            return redirect(url_for('cart.cart'))

    # =====================================================
    # ADDRESS
    # =====================================================

    address_id = request.form.get('address_id')

    if address_id:

        addr = Address.query.get_or_404(int(address_id))

        if addr.user_id != session['user_id']:

            flash('Invalid address.', 'error')

            return redirect(url_for('order.checkout'))

        full_name = addr.full_name
        phone = addr.phone
        address_line = addr.address_line
        city = addr.city
        state = addr.state
        pincode = addr.pincode

    else:

        full_name = request.form.get(
            'full_name',
            ''
        ).strip()

        phone = request.form.get(
            'phone',
            ''
        ).strip()

        address_line = request.form.get(
            'address_line',
            ''
        ).strip()

        city = request.form.get(
            'city',
            ''
        ).strip()

        state = request.form.get(
            'state',
            ''
        ).strip()

        pincode = request.form.get(
            'pincode',
            ''
        ).strip()

        if not all([
            full_name,
            phone,
            address_line,
            city,
            state,
            pincode
        ]):

            flash(
                'Please fill in all address fields.',
                'error'
            )

            return redirect(url_for('order.checkout'))

        # SAVE ADDRESS

        if request.form.get('save_address'):

            new_addr = Address(
                user_id=session['user_id'],
                full_name=full_name,
                phone=phone,
                address_line=address_line,
                city=city,
                state=state,
                pincode=pincode
            )

            db.session.add(new_addr)

    # =====================================================
    # STOCK CHECK
    # =====================================================

    for item in cart_items:

        product = Product.query.get(item.product_id)

        if product.stock_quantity < item.quantity:

            flash(
                f'"{product.name}" only has {product.stock_quantity} units available.',
                'error'
            )

            return redirect(url_for('cart.cart'))

    # =====================================================
    # TOTAL
    # =====================================================

    total = sum(item.subtotal for item in cart_items)

    payment_method = request.form.get(
        'payment_method',
        'COD'
    )

    custom_message = request.form.get(
        'custom_message',
        ''
    ).strip()

    # =====================================================
    # CREATE ORDER
    # =====================================================

    new_order = Order(
        user_id=session['user_id'],
        full_name=full_name,
        phone=phone,
        address_line=address_line,
        city=city,
        state=state,
        pincode=pincode,
        total_amount=total,
        status='PLACED',
        payment_status='PENDING',
        custom_message=custom_message,
    )

    db.session.add(new_order)

    db.session.flush()

    # =====================================================
    # CREATE ORDER ITEMS
    # =====================================================

    for item in cart_items:

        product = Product.query.get(item.product_id)

        item_notes = request.form.get(
            f'item_notes_{item.product_id}',
            ''
        ).strip()

        order_item = OrderItem(
            order_id=new_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=product.price,
            custom_text=item.product.name,
            custom_notes=item_notes,
        )

        db.session.add(order_item)

    # =====================================================
    # COD FLOW
    # =====================================================

    if payment_method == 'COD':

        for item in cart_items:

            product = Product.query.get(
                item.product_id
            )

            product.stock_quantity -= item.quantity

        payment = Payment(
            order_id=new_order.id,
            payment_method='COD',
            status='PENDING'
        )

        db.session.add(payment)

        # CLEAR CART

        if buy_now:

            session.pop('buy_now', None)

        else:

            Cart.query.filter_by(
                user_id=session['user_id']
            ).delete()

        db.session.commit()

        flash(
            'Order placed successfully!',
            'success'
        )

        return redirect(
            url_for(
                'order.order_detail',
                order_id=new_order.id
            )
        )

    # =====================================================
    # ONLINE PAYMENT FLOW
    # =====================================================

    elif payment_method == 'ONLINE':

        client = razorpay.Client(
            auth=(
                RAZORPAY_KEY_ID,
                RAZORPAY_KEY_SECRET
            )
        )

        razorpay_order = client.order.create({

            "amount": int(float(total) * 100),

            "currency": "INR",

            "payment_capture": 1

        })

        payment = Payment(
            order_id=new_order.id,
            payment_method='ONLINE',
            transaction_id=razorpay_order['id'],
            status='PENDING'
        )

        db.session.add(payment)

        db.session.commit()

        return render_template(

            'payment.html',

            order=new_order,

            razorpay_order_id=razorpay_order['id'],

            razorpay_key=RAZORPAY_KEY_ID,

            amount=int(total * 100)
        )

# =========================================================
# PAYMENT SUCCESS
# =========================================================

@order_bp.route('/payment/success', methods=['POST'])
@login_required
def payment_success():

    razorpay_payment_id = request.form.get(
        'razorpay_payment_id'
    )

    razorpay_order_id = request.form.get(
        'razorpay_order_id'
    )

    razorpay_signature = request.form.get(
        'razorpay_signature'
    )

    client = razorpay.Client(
        auth=(
            RAZORPAY_KEY_ID,
            RAZORPAY_KEY_SECRET
        )
    )

    # try:

    #     client.utility.verify_payment_signature({

    #         'razorpay_payment_id':
    #             razorpay_payment_id,

    #         'razorpay_order_id':
    #             razorpay_order_id,

    #         'razorpay_signature':
    #             razorpay_signature
    #     })

    # except Exception as e:
    #     print(e)
    #     flash(
    #         f'Payment verification failed: {str(e)}',
    #         'error'
    #     )
    #     return redirect(url_for('cart.cart'))

    payment = Payment.query.filter_by(
        transaction_id=razorpay_order_id
    ).first()

    if not payment:

        flash('Payment not found.', 'error')

        return redirect(url_for('cart.cart'))

    order = Order.query.get(payment.order_id)

    # AVOID DOUBLE PAYMENT

    if payment.status == 'SUCCESS':

        return redirect(
            url_for(
                'order.order_detail',
                order_id=order.id
            )
        )

    # =====================================================
    # PAYMENT SUCCESS
    # =====================================================

    payment.status = 'SUCCESS'

    order.payment_status = 'PAID'

    # REDUCE STOCK

    for item in order.items:

        product = Product.query.get(
            item.product_id
        )

        if product:

            product.stock_quantity -= item.quantity

    # CLEAR CART

    buy_now = session.get('buy_now')

    if buy_now:

        session.pop('buy_now', None)

    else:

        Cart.query.filter_by(
            user_id=session['user_id']
        ).delete()

    db.session.commit()

    flash(
        'Payment successful!',
        'success'
    )

    return redirect(
        url_for(
            'order.order_detail',
            order_id=order.id
        )
    )

# =========================================================
# PAYMENT FAILED
# =========================================================

@order_bp.route('/payment/failed')
@login_required
def payment_failed():

    razorpay_order_id = request.args.get(
        'razorpay_order_id'
    )

    if razorpay_order_id:

        payment = Payment.query.filter_by(
            transaction_id=razorpay_order_id
        ).first()

        if payment:

            order = Order.query.get(
                payment.order_id
            )

            # DELETE ORDER ITEMS
            if order:

                OrderItem.query.filter_by(
                    order_id=order.id
                ).delete()

                # DELETE PAYMENT
                db.session.delete(payment)

                # DELETE ORDER
                db.session.delete(order)

                db.session.commit()

    flash(
        'Payment failed or cancelled.',
        'error'
    )

    return redirect(url_for('cart.cart'))
# =========================================================
# ORDER HISTORY
# =========================================================

@order_bp.route('/history', methods=['GET'])
@login_required
def order_history():

    orders = Order.query.filter_by(
        user_id=session['user_id']
    ).order_by(
        Order.created_at.desc()
    ).all()

    return render_template(
        'order_history.html',
        orders=orders
    )

# =========================================================
# ORDER DETAIL
# =========================================================

@order_bp.route('/<int:order_id>', methods=['GET'])
@login_required
def order_detail(order_id):

    order = Order.query.get_or_404(order_id)

    if (
        order.user_id != session['user_id']
        and not session.get('admin')
    ):

        flash('Unauthorized.', 'error')

        return redirect(
            url_for('order.order_history')
        )

    return render_template(
        'order_detail.html',
        order=order
    )

# =========================================================
# CANCEL ORDER
# =========================================================

@order_bp.route('/cancel/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):

    order = Order.query.get_or_404(order_id)

    if order.user_id != session['user_id']:

        flash('Unauthorized.', 'error')

        return redirect(
            url_for('order.order_history')
        )

    if order.status not in (
        'PLACED',
        'CONFIRMED'
    ):

        flash(
            'Order cannot be cancelled at this stage.',
            'error'
        )

        return redirect(
            url_for(
                'order.order_detail',
                order_id=order_id
            )
        )

    # RESTORE STOCK

    for item in order.items:

        product = Product.query.get(
            item.product_id
        )

        if product:

            product.stock_quantity += item.quantity

    order.status = 'CANCELLED'

    db.session.commit()

    flash('Order cancelled.', 'success')

    return redirect(
        url_for('order.order_history')
    )
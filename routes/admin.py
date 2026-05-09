from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import db
from werkzeug.utils import secure_filename
from models.category import Category
from models.product import Product
from models.user import User
from models.productimage import ProductImage
from models.order import Order
from decorators import admin_required   # FIX: import decorator
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}   # FIX: file type whitelist


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file, product_id):
    """Save uploaded image and return db_path or None."""
    if not file or file.filename == '':
        return None
    if not allowed_file(file.filename):               # FIX: validate file type
        flash('Only PNG, JPG, JPEG, WEBP images allowed.', 'error')
        return None
    filename = secure_filename(file.filename)
    upload_folder = os.path.join('static', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    file.save(os.path.join(upload_folder, filename))
    return f'uploads/{filename}'


# ─── Dashboard ────────────────────────────────────────────────────────────────

@admin_bp.route('/dashboard')
@admin_required                          # FIX: protect every admin route
def dashboard():
    total_products = Product.query.count()
    total_users    = User.query.filter_by(role='CUSTOMER').count()
    total_orders   = Order.query.count()
    pending_orders = Order.query.filter_by(status='PLACED').count()
    return render_template('/admin/dashboard.html',
        total_products=total_products,
        total_users=total_users,
        total_orders=total_orders,
        pending_orders=pending_orders
    )


# ─── Categories ───────────────────────────────────────────────────────────────

@admin_bp.route('/categories')           # FIX: typo was /categorys
@admin_required
def category():
    categorys = Category.query.all()
    return render_template('/admin/category.html', categorys=categorys)


@admin_bp.route('/category/add', methods=['GET', 'POST'])
@admin_required
def add_category():
    if request.method == 'POST':
        name = request.form.get('category', '').strip()
        if not name:
            flash('Category name is required.', 'error')
            return redirect(url_for('admin.category'))
        if Category.query.filter_by(name=name).first():
            flash('Category already exists.', 'error')
            return redirect(url_for('admin.category'))
        db.session.add(Category(name=name))
        db.session.commit()
        flash('Category added.', 'success')
        return redirect(url_for('admin.category'))
    return render_template('/admin/category.html')


@admin_bp.route('/category/delete/<int:id>', methods=['POST'])   # FIX: POST not GET
@admin_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted.', 'success')
    return redirect(url_for('admin.category'))


@admin_bp.route('/category/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    if request.method == 'POST':
        name = request.form.get('category', '').strip()
        if not name:
            flash('Category name is required.', 'error')
            return redirect(url_for('admin.category'))
        category.name = name
        db.session.commit()
        flash('Category updated.', 'success')
        return redirect(url_for('admin.category'))
    return render_template('/admin/category.html', category=category)


# ─── Products ─────────────────────────────────────────────────────────────────

@admin_bp.route('/products')
@admin_required
def product():
    products = Product.query.all()
    return render_template('/admin/product.html', products=products)


@admin_bp.route('/product/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        price    = request.form.get('price')
        stock    = request.form.get('stock_quantity')
        cat_id   = request.form.get('category_id')

        # FIX: validate numeric fields
        try:
            price = float(price)
            stock = int(stock)
            assert price > 0 and stock >= 0
        except (ValueError, TypeError, AssertionError):
            flash('Price must be a positive number and stock must be 0 or more.', 'error')
            return redirect(url_for('admin.add_product'))

        new_product = Product(
            name=name,
            description=request.form.get('description'),
            price=price,
            stock_quantity=stock,
            category_id=int(cat_id),
        )
        db.session.add(new_product)
        db.session.flush()

        images = request.files.getlist('images')

        for image in images:
            db_path = save_image(image, new_product.id)
            if db_path:
                db.session.add(
                ProductImage(
                    product_id=new_product.id,
                    image_url=db_path
                )
            )

        db.session.commit()
        flash('Product added.', 'success')
        return redirect(url_for('admin.product'))

    categorys = Category.query.all()
    return render_template('/admin/add_product.html', categorys=categorys)


@admin_bp.route('/product/toggle/<int:id>', methods=['POST'])
@admin_required
def toggle_product(id):

    product = Product.query.get_or_404(id)

    product.is_active = not product.is_active

    db.session.commit()

    if product.is_active:
        flash(
            f'{product.name} activated successfully.',
            'success'
        )
    else:
        flash(
            f'{product.name} deactivated successfully.',
            'success'
        )
    return redirect(
        url_for('admin.product')
    )


@admin_bp.route('/product/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_product(id):
    product   = Product.query.get_or_404(id)
    categorys = Category.query.all()

    if request.method == 'POST':
        price = request.form.get('price')
        stock = request.form.get('stock_quantity')

        try:
            price = float(price)
            stock = int(stock)
            assert price > 0 and stock >= 0
        except (ValueError, TypeError, AssertionError):
            flash('Price must be a positive number and stock must be 0 or more.', 'error')
            return render_template('/admin/add_product.html', product=product, categorys=categorys)

        product.name         = request.form.get('name')
        product.description  = request.form.get('description')
        product.price        = price
        product.stock_quantity = stock
        product.category_id  = int(request.form.get('category_id'))

        images = request.files.getlist('images')

        if images and images[0].filename != '':

            # OPTIONAL:
            # delete old images first

            old_images = ProductImage.query.filter_by(
                product_id=product.id
            ).all()

            for old in old_images:
                db.session.delete(old)

            # save new images

            for image in images:

                db_path = save_image(image, product.id)

                if db_path:
                    db.session.add(
                        ProductImage(
                            product_id=product.id,
                            image_url=db_path
                        )
                    )
        db.session.commit()
        flash('Product updated.', 'success')
        return redirect(url_for('admin.product'))

    return render_template('/admin/add_product.html', product=product, categorys=categorys)


# ─── Users ────────────────────────────────────────────────────────────────────

@admin_bp.route('/users', methods=['GET'])
@admin_required
def users():
    users = User.query.all()
    return render_template('/admin/users.html', users=users)


@admin_bp.route('/user/switch/<int:user_id>/<string:user_role>', methods=['POST'])  # FIX: POST
@admin_required
def switch_user(user_id, user_role):
    user = User.query.get_or_404(user_id)
    user.role = 'CUSTOMER' if user_role == 'ADMIN' else 'ADMIN'
    db.session.commit()
    flash(f'User role updated to {user.role}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/user/delete/<int:user_id>', methods=['POST'])   # FIX: POST
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted.', 'success')
    return redirect(url_for('admin.users'))


# ─── ADMIN: All orders ────────────────────────────────────────────────────────

@admin_bp.route('/orders', methods=['GET'])
@admin_required
def admin_orders():
    status_filter = request.args.get('status')
    query = Order.query.order_by(Order.created_at.desc())
    if status_filter:
        query = query.filter_by(status=status_filter)
    orders = query.all()
    return render_template('admin/orders.html', orders=orders, status_filter=status_filter)


# ─── ADMIN: Update order status ──────────────────────────────────────────────

@admin_bp.route('/orders/<int:order_id>/status', methods=['POST'])
@admin_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')

    valid_statuses = ['PLACED', 'CONFIRMED', 'PACKED', 'SHIPPED', 'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED']
    if new_status not in valid_statuses:
        flash('Invalid status.', 'error')
        return redirect(url_for('admin.admin_orders'))

    order.status = new_status

    # Mark payment as PAID when delivered (COD)
    if new_status == 'DELIVERED' and order.payment and order.payment.payment_method == 'COD':
        order.payment.status = 'SUCCESS'
        order.payment_status = 'PAID'

    db.session.commit()
    flash(f'Order #{order_id} updated to {new_status}.', 'success')
    return redirect(url_for('admin.admin_orders'))

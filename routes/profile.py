from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import db
from models.user import User
from models.address import Address
from werkzeug.security import generate_password_hash, check_password_hash
from decorators import login_required

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')


# ─── View Profile ─────────────────────────────────────────────────────────────

@profile_bp.route('/', methods=['GET'])
@login_required
def profile():
    user = User.query.get_or_404(session['user_id'])
    addresses = Address.query.filter_by(user_id=session['user_id']).all()
    return render_template('profile.html', user=user, addresses=addresses)


# ─── Edit Profile ─────────────────────────────────────────────────────────────

@profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = User.query.get_or_404(session['user_id'])
    if request.method == 'POST':
        name  = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        if not name:
            flash('Name cannot be empty.', 'error')
            return render_template('edit_profile.html', user=user)
        user.name  = name
        user.phone = phone
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('profile.profile'))
    return render_template('edit_profile.html', user=user)


# ─── Change Password ──────────────────────────────────────────────────────────

@profile_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    user = User.query.get_or_404(session['user_id'])
    if request.method == 'POST':
        current  = request.form.get('current_password', '')
        new_pass = request.form.get('new_password', '')
        confirm  = request.form.get('confirm_password', '')

        if not check_password_hash(user.password, current):
            flash('Current password is incorrect.', 'error')
            return render_template('change_password.html')
        if new_pass != confirm:
            flash('New passwords do not match.', 'error')
            return render_template('change_password.html')
        if len(new_pass) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('change_password.html')

        user.password = generate_password_hash(new_pass)
        db.session.commit()
        flash('Password changed successfully.', 'success')
        return redirect(url_for('profile.profile'))
    return render_template('change_password.html')


# ─── Add Address ──────────────────────────────────────────────────────────────

@profile_bp.route('/address/add', methods=['GET', 'POST'])
@login_required
def add_address():
    if request.method == 'POST':
        addr = Address(
            user_id    = session['user_id'],
            full_name  = request.form.get('full_name', '').strip(),
            phone      = request.form.get('phone', '').strip(),
            address_line = request.form.get('address_line', '').strip(),
            city       = request.form.get('city', '').strip(),
            state      = request.form.get('state', '').strip(),
            pincode    = request.form.get('pincode', '').strip(),
            is_default = bool(request.form.get('is_default'))
        )
        if not all([addr.full_name, addr.phone, addr.address_line, addr.city, addr.state, addr.pincode]):
            flash('All address fields are required.', 'error')
            return render_template('add_address.html')

        # if marked default, unset previous default
        if addr.is_default:
            Address.query.filter_by(user_id=session['user_id'], is_default=True)\
                .update({'is_default': False})

        db.session.add(addr)
        db.session.commit()
        flash('Address saved.', 'success')
        return redirect(url_for('profile.profile'))
    return render_template('add_address.html')


@profile_bp.route('/address/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_address(id):
    address = Address.query.get_or_404(id)
    if request.method == 'POST':
        user_id    = session['user_id'],
        full_name  = request.form.get('full_name', '').strip(),
        phone      = request.form.get('phone', '').strip(),
        address_line = request.form.get('address_line', '').strip(),
        city       = request.form.get('city', '').strip(),
        state      = request.form.get('state', '').strip(),
        pincode    = request.form.get('pincode', '').strip(),
        is_default = bool(request.form.get('is_default'))

        if not all([full_name, phone, address_line, city, state, pincode]):
            flash('All address fields are required.', 'error')
            return render_template('add_address.html')
        address.full_name  = full_name
        address.phone = phone
        address.address_line = address_line
        address.city = city
        address.state = state
        address.pincode = pincode
        address.is_default = is_default

        db.session.commit()
        flash('Addess updated.', 'success')
        return redirect(url_for('profile.profile'))
    return render_template('add_address.html',
                           address=address
                           )

# ─── Delete Address ───────────────────────────────────────────────────────────

@profile_bp.route('/address/delete/<int:addr_id>', methods=['POST'])
@login_required
def delete_address(addr_id):
    addr = Address.query.get_or_404(addr_id)
    if addr.user_id != session['user_id']:
        flash('Unauthorized.', 'error')
        return redirect(url_for('profile.profile'))
    db.session.delete(addr)
    db.session.commit()
    flash('Address removed.', 'success')
    return redirect(url_for('profile.profile'))


# ─── Set Default Address ──────────────────────────────────────────────────────

@profile_bp.route('/address/set-default/<int:addr_id>', methods=['POST'])
@login_required
def set_default_address(addr_id):
    addr = Address.query.get_or_404(addr_id)
    if addr.user_id != session['user_id']:
        flash('Unauthorized.', 'error')
        return redirect(url_for('profile.profile'))
    Address.query.filter_by(user_id=session['user_id'], is_default=True)\
        .update({'is_default': False})
    addr.is_default = True
    db.session.commit()
    flash('Default address updated.', 'success')
    return redirect(url_for('profile.profile'))

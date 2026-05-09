from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    """Use on any route that needs a logged-in customer."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to continue.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Use on every admin route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            flash('Admin access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

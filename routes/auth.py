from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from database import db
from models.user import User
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import random
import smtplib
import time
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

EMAIL = os.environ.get('EMAIL')
PASSWORD = os.environ.get('PASSWORD')# from Google


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if not user:
            flash('No account found with this email.', 'error')   # FIX: was returning plain string
            return render_template('login.html')

        if not check_password_hash(user.password, password):
            flash('Incorrect password.', 'error')                  # FIX: was returning plain string
            return render_template('login.html')

        if not user.is_active:
            flash('Your account has been deactivated.', 'error')
            return render_template('login.html')

        # FIX: store user_id for ALL users including admin
        session['user_id'] = user.id
        session['email'] = user.email
        session['role'] = user.role

        if user.role == 'ADMIN':
            session['admin'] = True
            return redirect(url_for('admin.dashboard'))

        return redirect(url_for('index'))

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()

        # FIX: check for existing email before inserting
        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'error')
            return render_template('register.html')

        # FIX: basic validation
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html')

        new_user = User(
            name=username,
            email=email,
            password=generate_password_hash(password),
            phone=phone,
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/google')
def google_login():
    redirect_uri = "http://127.0.0.1:5000/auth/google/callback"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    url = GOOGLE_AUTH_URL + "?" + "&".join(
        [f"{k}={v}" for k, v in params.items()]
    )
    return redirect(url)


@auth_bp.route('/google/callback')
def google_callback():
    code = request.args.get('code')
    if not code:
        return "Authorization failed", 400

    # Exchange code for access token
    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": url_for("auth.google_callback", _external=True),
        "grant_type": "authorization_code"
    }

    token_response = requests.post(GOOGLE_TOKEN_URL, data=token_data)
    token_json = token_response.json()

    access_token = token_json.get("access_token")
    if not access_token:
        return "Failed to get access token", 400

    # Get user info from Google
    userinfo_response = requests.get(
        GOOGLE_USERINFO_URL,
        params={"access_token": access_token}
    )

    userinfo = userinfo_response.json()

    email = userinfo.get("email")
    name = userinfo.get("name")

    if not email:
        return "Google login failed", 400

    # Check if user already exists
    user = User.query.filter_by(email=email).first()

    if not user:
        user = User(
            name=name,
            email=email,
            google_id=userinfo.get("sub"),
            password=None,   # No password for Google users
            role='CUSTOMER'
        )
        db.session.add(user)
    else:
        if not user.google_id:
            user.google_id = userinfo.get("sub")
    db.session.commit()
    session['email'] = email
    session['user_id'] = user.id
    session['role'] = user.role
    return redirect(url_for('index'))



# Verify page
@auth_bp.route('/verify-email',methods=['GET'])
def verify_email_page():
    show_otp = request.args.get('show_otp')
    email = request.args.get('email')
    return render_template('verify.html', show_otp=show_otp, email=email)


@auth_bp.route('/send-email-otp', methods=['POST'])
def send_email_otp():
    resend = request.form.get('resend',False)
    if resend != False:
        user_email = session.get('email')
    else:
        user_email = request.form.get('email')
    
    users = User.query.filter_by(email=user_email).first()
    if users:
        otp = str(random.randint(100000, 999999))
        session['otp'] = otp
        session['expiry'] = time.time() + 120
        session['email'] = user_email
        session['name'] = request.form.get('name')
        # Send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL, PASSWORD)

        message = f"Subject: Email Verification\n\nYour OTP is {otp}"

        server.sendmail(EMAIL, user_email, message.encode('utf-8'))
        server.quit()

        print("OTP:", otp)

        return redirect(url_for('auth.verify_email_page', show_otp=1, email=user_email))
    else:
        return redirect('/auth/verify-email?error=User%20Does%20not%20Exist')

# Verify OTP
@auth_bp.route('/verify-email-otp', methods=['POST'])
def verify_email_otp():
    user_otp = request.form.get('otp')

    if time.time() > session.get('expiry', 0):
        flash("OTP expired. Please request a new one.", "error")
        return redirect(url_for('auth.verify_email_otp'))

    if user_otp == session.get('otp'):
        return redirect(url_for('auth.newpassword'))
    else:
        flash("Invalid OTP. Please try again.", "error")
        return redirect(url_for('auth.verify_email_page', show_otp=1, email=session.get('email'),otp=user_otp))
    
@auth_bp.route('newpassword',methods=['GET','POST'])
def newpassword():
    if request.method == 'POST':
        email = session.get('email')
        new_password = request.form.get('password')

        User.query.filter_by(email=email).update({
        User.password: generate_password_hash(new_password)
        })
        db.session.commit()

        return redirect(url_for('auth.login'))
    return render_template('newpassword.html')




@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

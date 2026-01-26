# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Authentication routes (login, logout, signup).
See instructions/architecture for development guidelines.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, UserSignupRequest
from app.utils.auth import hash_password, verify_password, generate_username

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler."""
    if current_user.is_authenticated:
        return redirect(url_for('home.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        if not username or not password:
            flash('Please provide both username and password.', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and verify_password(password, user.password_hash):
            login_user(user, remember=remember)
            next_page = request.args.get('next') or url_for('home.index')
            return redirect(next_page)
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    """Logout handler."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page and handler."""
    if current_user.is_authenticated:
        return redirect(url_for('home.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')  # 'requester' or 'dev'
        
        if not all([name, email, password, role]):
            flash('Please fill in all fields.', 'error')
            return render_template('auth/signup.html')
        
        if role not in ['requester', 'dev']:
            flash('Invalid role selected.', 'error')
            return render_template('auth/signup.html')
        
        # Generate username if not provided
        if not username:
            username = generate_username(name, email)
        
        # Validate username format
        import re
        if not re.match(r'^[a-zA-Z0-9_]{3,}$', username):
            flash('Username must be at least 3 characters and contain only letters, numbers, and underscores.', 'error')
            return render_template('auth/signup.html')
        
        # Check if username already exists
        if User.query.filter_by(username=username).first() or UserSignupRequest.query.filter_by(username=username).first():
            flash('Username already taken. Please choose a different username.', 'error')
            return render_template('auth/signup.html')
        
        # Check if email already exists
        if User.query.filter_by(email=email).first() or UserSignupRequest.query.filter_by(email=email).first():
            flash('Email address already registered.', 'error')
            return render_template('auth/signup.html')
        
        # Create signup request
        signup_request = UserSignupRequest(
            username=username,
            name=name,
            email=email,
            password_hash=hash_password(password),
            requested_role=role,
            email_verified=False
        )
        db.session.add(signup_request)
        db.session.commit()
        
        # Create and send verification email
        from app.utils.email_verification import create_verification_token, send_verification_email_for_token
        token = create_verification_token(
            email=email,
            verification_type='signup',
            signup_request_id=signup_request.id
        )
        
        # Send email (get base URL from request)
        base_url = request.url_root.rstrip('/')
        send_verification_email_for_token(token, base_url)
        
        flash('Sign-up request created. Please check your email for verification.', 'info')
        return redirect(url_for('auth.check_email'))
    
    return render_template('auth/signup.html')

@bp.route('/check-email')
def check_email():
    """Check your email page."""
    return render_template('auth/check_email.html')

@bp.route('/verify-email')
def verify_email():
    """Email verification endpoint."""
    token_string = request.args.get('token')
    
    if not token_string:
        flash('Invalid verification link.', 'error')
        return redirect(url_for('auth.login'))
    
    from app.utils.email_verification import verify_token
    success, token, error_message = verify_token(token_string)
    
    if not success:
        flash(error_message, 'error')
        return redirect(url_for('auth.login'))
    
    # Update signup request or user email verification status
    if token.verification_type == 'signup' and token.signup_request_id:
        signup_request = UserSignupRequest.query.get(token.signup_request_id)
        if signup_request:
            signup_request.email_verified = True
            db.session.commit()
            # Redirect to quiz
            return redirect(url_for('quiz.take_quiz', signup_request_id=signup_request.id))
    elif token.verification_type == 'signup' and token.user_id:
        # Existing user verifying their email (resend verification)
        user = User.query.get(token.user_id)
        if user:
            user.email_verified = True
            db.session.commit()
            flash('Email verified successfully!', 'success')
            # Redirect to account settings if user is logged in, otherwise to login
            if current_user.is_authenticated:
                return redirect(url_for('account.settings'))
            return redirect(url_for('auth.login'))
    elif token.verification_type == 'email_change' and token.user_id:
        user = User.query.get(token.user_id)
        if user:
            user.email = token.email
            user.email_verified = True
            db.session.commit()
            flash('Email address updated and verified!', 'success')
    
    return redirect(url_for('auth.login'))


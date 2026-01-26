# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Admin routes.
See instructions/architecture for development guidelines.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, send_from_directory, abort, session
from flask_login import login_required, current_user, login_user
from functools import wraps
from app import db
from app.models import User, UserSignupRequest, RoleChangeRequest, App, FeatureRequest, NotificationPreference
from app.config import load_config, save_config, load_email_config, save_email_config, load_email_templates, save_email_templates, load_stripe_config, save_stripe_config, get_stripe_key
from app.utils.email import send_email
from app.utils.stats import get_admin_stats
import os
import json
from pathlib import Path
import shutil
from datetime import datetime
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

bp = Blueprint('admin', __name__, url_prefix='/admin')

def require_admin(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@bp.route('')
@login_required
@require_admin
def index():
    """Admin panel landing page."""
    stats = get_admin_stats()
    return render_template('admin/index.html', stats=stats)

@bp.route('/users')
@login_required
@require_admin
def users():
    """User management page."""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get search parameters
    search_column = request.args.get('search_column', '')
    search_value = request.args.get('search_value', '')
    
    # Get sort parameters
    sort_column = request.args.get('sort_column', 'id')
    sort_order = request.args.get('sort_order', 'desc')  # 'asc' or 'desc'
    
    # Build query
    query = User.query
    
    # Apply search filter if provided
    if search_column and search_value:
        search_value_lower = search_value.lower()
        if search_column == 'id':
            try:
                search_id = int(search_value)
                query = query.filter(User.id == search_id)
            except ValueError:
                pass  # Invalid ID, ignore
        elif search_column == 'name':
            query = query.filter(User.name.ilike(f'%{search_value}%'))
        elif search_column == 'username':
            query = query.filter(User.username.ilike(f'%{search_value}%'))
        elif search_column == 'email':
            query = query.filter(User.email.ilike(f'%{search_value}%'))
        elif search_column == 'role':
            query = query.filter(User.role.ilike(f'%{search_value}%'))
        elif search_column == 'email_verified':
            # Handle Yes/No or True/False
            if search_value_lower in ['yes', 'true', '1']:
                query = query.filter(User.email_verified == True)
            elif search_value_lower in ['no', 'false', '0']:
                query = query.filter(User.email_verified == False)
    
    # Apply sorting
    valid_sort_columns = ['id', 'name', 'username', 'email', 'role', 'email_verified']
    if sort_column not in valid_sort_columns:
        sort_column = 'id'
    
    if sort_order not in ['asc', 'desc']:
        sort_order = 'desc'
    
    # Map sort column to User model attributes
    sort_attr = getattr(User, sort_column, User.id)
    if sort_order == 'asc':
        query = query.order_by(sort_attr.asc())
    else:
        query = query.order_by(sort_attr.desc())
    
    # Paginate results
    users_pagination = query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    signup_requests = UserSignupRequest.query.filter_by(status='pending').all()
    role_change_requests = RoleChangeRequest.query.filter_by(status='pending').all()
    return render_template('admin/users.html', 
                         users=users_pagination.items,
                         pagination=users_pagination,
                         search_column=search_column,
                         search_value=search_value,
                         sort_column=sort_column,
                         sort_order=sort_order,
                         signup_requests=signup_requests,
                         role_change_requests=role_change_requests)

@bp.route('/users/<int:user_id>/approve', methods=['POST'])
@login_required
@require_admin
def approve_user(user_id):
    """Approve a user signup request."""
    signup_request = UserSignupRequest.query.get_or_404(user_id)
    
    if signup_request.status != 'pending':
        flash('This signup request has already been processed.', 'error')
        return redirect(url_for('admin.users'))
    
    # Create user account
    from app.models import User
    user = User(
        username=signup_request.username,
        name=signup_request.name,
        email=signup_request.email,
        password_hash=signup_request.password_hash,
        email_verified=signup_request.email_verified,
        role=signup_request.requested_role
    )
    db.session.add(user)
    
    # Update signup request
    signup_request.status = 'approved'
    signup_request.reviewed_by_id = current_user.id
    signup_request.reviewed_at = datetime.utcnow()
    
    db.session.commit()
    
    flash(f'User {user.username} approved successfully!', 'success')
    return redirect(url_for('admin.users'))

@bp.route('/users/<int:user_id>/deny', methods=['POST'])
@login_required
@require_admin
def deny_user(user_id):
    """Deny a user signup request."""
    signup_request = UserSignupRequest.query.get_or_404(user_id)
    
    if signup_request.status != 'pending':
        flash('This signup request has already been processed.', 'error')
        return redirect(url_for('admin.users'))
    
    signup_request.status = 'denied'
    signup_request.reviewed_by_id = current_user.id
    signup_request.reviewed_at = datetime.utcnow()
    
    db.session.commit()
    
    flash('Signup request denied.', 'info')
    return redirect(url_for('admin.users'))

@bp.route('/role-change-requests/<int:request_id>/approve', methods=['POST'])
@login_required
@require_admin
def approve_role_change(request_id):
    """Approve a role change request."""
    role_change_request = RoleChangeRequest.query.get_or_404(request_id)
    
    if role_change_request.status != 'pending':
        flash('This role change request has already been processed.', 'error')
        return redirect(url_for('admin.users'))
    
    # Update user's role
    user = role_change_request.user
    if user.role != 'requester':
        flash('Only requester accounts can be upgraded to dev.', 'error')
        return redirect(url_for('admin.users'))
    
    user.role = role_change_request.requested_role
    
    # Update role change request
    role_change_request.status = 'approved'
    role_change_request.reviewed_by_id = current_user.id
    role_change_request.reviewed_at = datetime.utcnow()
    
    db.session.commit()
    
    flash(f'Role change request approved! {user.username} is now a developer.', 'success')
    return redirect(url_for('admin.users'))

@bp.route('/role-change-requests/<int:request_id>/deny', methods=['POST'])
@login_required
@require_admin
def deny_role_change(request_id):
    """Deny a role change request."""
    role_change_request = RoleChangeRequest.query.get_or_404(request_id)
    
    if role_change_request.status != 'pending':
        flash('This role change request has already been processed.', 'error')
        return redirect(url_for('admin.users'))
    
    role_change_request.status = 'denied'
    role_change_request.reviewed_by_id = current_user.id
    role_change_request.reviewed_at = datetime.utcnow()
    
    db.session.commit()
    
    flash('Role change request denied.', 'info')
    return redirect(url_for('admin.users'))

@bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@require_admin
def reset_user_password(user_id):
    """Send password reset email to user."""
    user = User.query.get_or_404(user_id)
    
    # Create password reset token
    from app.utils.email_verification import create_verification_token
    token = create_verification_token(
        email=user.email,
        verification_type='password_reset',
        user_id=user.id
    )
    
    # Send password reset email
    from app.utils.email import send_email
    import json
    from pathlib import Path
    
    # Load email templates
    instance_path = Path(__file__).parent.parent.parent / 'instance'
    templates_file = instance_path / 'email_templates.json'
    if templates_file.exists():
        with open(templates_file, 'r') as f:
            templates = json.load(f)
    else:
        templates = {}
    
    reset_template = templates.get('password_reset', {})
    subject = reset_template.get('subject', 'Password Reset Request')
    body_template = reset_template.get('body', '<p>Click <a href="{reset_link}">here</a> to reset your password.</p>')
    
    base_url = request.url_root.rstrip('/')
    reset_link = f"{base_url}/account/reset-password?token={token.token}"
    
    body = body_template.format(
        user_name=user.name,
        reset_link=reset_link
    )
    
    email_sent = send_email(user.email, subject, body)
    
    if email_sent:
        flash(f'Password reset email sent to {user.email}.', 'success')
    else:
        flash(f'Failed to send password reset email to {user.email}. Please check email configuration.', 'error')
    
    return redirect(url_for('admin.users'))

@bp.route('/apps')
@login_required
@require_admin
def apps():
    """App management page."""
    apps_list = App.query.all()
    return render_template('admin/apps.html', apps=apps_list)

@bp.route('/apps/create', methods=['GET', 'POST'])
@login_required
@require_admin
def create_app():
    """Create new app."""
    if request.method == 'POST':
        app_name = request.form.get('app_name')
        app_display_name = request.form.get('app_display_name')
        app_description = request.form.get('app_description')
        app_url = request.form.get('app_url')
        github_url = request.form.get('github_url')
        
        # Validate app_name (URL-safe)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', app_name):
            flash('App name must contain only alphanumeric characters, hyphens, and underscores.', 'error')
            return render_template('admin/app_create.html')
        
        # Check if app_name already exists
        if App.query.filter_by(app_name=app_name).first():
            flash('App name already exists.', 'error')
            return render_template('admin/app_create.html')
        
        app = App(
            app_name=app_name,
            app_display_name=app_display_name,
            app_description=app_description,
            app_url=app_url,
            github_url=github_url,
            app_owner_id=current_user.id
        )
        db.session.add(app)
        db.session.flush()  # Flush to get the app ID
        
        # Automatically create a notification rule for the app owner
        
        pref = NotificationPreference.query.filter_by(
            user_id=current_user.id,
            notification_type='new_request'
        ).first()
        
        # Parse existing custom rules
        custom_rules = []
        if pref and pref.custom_rule:
            try:
                custom_rules = json.loads(pref.custom_rule)
            except:
                custom_rules = []
        
        # Add rule for the new app with default preference of 'immediate'
        custom_rules.append({
            'app_id': app.id,
            'app_name': app.app_display_name,
            'preference': 'immediate'
        })
        
        # Update or create preference
        if pref:
            pref.custom_rule = json.dumps(custom_rules)
            pref.updated_at = datetime.utcnow()
        else:
            pref = NotificationPreference(
                user_id=current_user.id,
                notification_type='new_request',
                preference='none',  # Default to none since we're using app-specific rules
                custom_rule=json.dumps(custom_rules)
            )
            db.session.add(pref)
        
        db.session.commit()
        
        flash('App created successfully! A notification rule has been automatically added for this app.', 'success')
        return redirect(url_for('admin.apps'))
    
    return render_template('admin/app_create.html')

@bp.route('/apps/<int:app_id>/edit', methods=['GET', 'POST'])
@login_required
@require_admin
def edit_app(app_id):
    """Edit app."""
    app = App.query.get_or_404(app_id)
    
    if request.method == 'POST':
        app.app_display_name = request.form.get('app_display_name')
        app.app_description = request.form.get('app_description')
        app.app_url = request.form.get('app_url')
        app.github_url = request.form.get('github_url')
        
        # Handle icon upload
        if 'icon' in request.files:
            file = request.files['icon']
            if file and file.filename:
                try:
                    instance_path = Path(__file__).parent.parent.parent / 'instance' / 'uploads'
                    instance_path.mkdir(parents=True, exist_ok=True)
                    icon_filename = f'app_{app_id}_icon.png'
                    icon_path = instance_path / icon_filename
                    file.save(icon_path)
                    app.icon_path = f'uploads/{icon_filename}'
                    flash('Icon uploaded successfully!', 'success')
                except Exception as e:
                    flash(f'Error uploading icon: {str(e)}', 'error')
        
        db.session.commit()
        flash('App updated successfully!', 'success')
        return redirect(url_for('admin.apps'))
    
    return render_template('admin/app_edit.html', app=app)

@bp.route('/icon')
def serve_icon():
    """Serve the Feature Requestor icon from instance folder."""
    instance_path = Path(__file__).parent.parent.parent / 'instance'
    icon_path = instance_path / 'icon.png'
    
    if not icon_path.exists():
        abort(404)
    
    return send_file(str(icon_path), mimetype='image/png')

@bp.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Serve uploaded files from instance/uploads folder."""
    instance_path = Path(__file__).parent.parent.parent / 'instance' / 'uploads'
    
    # Normalize filename to prevent directory traversal
    filename = filename.lstrip('/')
    filename = filename.replace('\\', '/')  # Normalize path separators
    if '..' in filename or filename.startswith('/'):
        abort(404)
    
    file_path = instance_path / filename
    
    # Security check: ensure file is within uploads directory
    try:
        resolved_file = file_path.resolve()
        resolved_instance = instance_path.resolve()
        resolved_file.relative_to(resolved_instance)
    except (ValueError, OSError):
        abort(404)
    
    if not file_path.exists():
        abort(404)
    
    # Use send_from_directory for better path handling
    # Determine MIME type based on file extension
    mimetype = None
    if filename.lower().endswith('.png'):
        mimetype = 'image/png'
    elif filename.lower().endswith(('.jpg', '.jpeg')):
        mimetype = 'image/jpeg'
    elif filename.lower().endswith('.gif'):
        mimetype = 'image/gif'
    elif filename.lower().endswith('.webp'):
        mimetype = 'image/webp'
    elif filename.lower().endswith('.svg'):
        mimetype = 'image/svg+xml'
    
    response = send_from_directory(str(instance_path), filename, mimetype=mimetype)
    return response

@bp.route('/apps/<int:app_id>/fetch-icon', methods=['POST'])
@login_required
@require_admin
def fetch_app_icon(app_id):
    """Fetch favicon from app URL."""
    app = App.query.get_or_404(app_id)
    
    if not app.app_url:
        flash('App URL is required to fetch icon.', 'error')
        return redirect(url_for('admin.edit_app', app_id=app_id))
    
    try:
        # Fetch the app URL
        response = requests.get(app.app_url, timeout=10, allow_redirects=True)
        response.raise_for_status()
        
        # Parse HTML to find favicon
        soup = BeautifulSoup(response.text, 'html.parser')
        favicon_url = None
        
        # Try to find favicon link
        favicon_link = soup.find('link', rel=lambda x: x and ('icon' in x.lower() or 'shortcut' in x.lower()))
        if favicon_link and favicon_link.get('href'):
            favicon_url = urljoin(app.app_url, favicon_link['href'])
        else:
            # Try common favicon locations
            base_url = urlparse(app.app_url)
            common_paths = ['/favicon.ico', '/favicon.png', '/apple-touch-icon.png']
            for path in common_paths:
                test_url = f"{base_url.scheme}://{base_url.netloc}{path}"
                try:
                    test_response = requests.head(test_url, timeout=5, allow_redirects=True)
                    if test_response.status_code == 200:
                        favicon_url = test_url
                        break
                except:
                    continue
        
        if not favicon_url:
            flash('Could not find favicon on the app URL.', 'error')
            return redirect(url_for('admin.edit_app', app_id=app_id))
        
        # Download the favicon
        icon_response = requests.get(favicon_url, timeout=10, allow_redirects=True)
        icon_response.raise_for_status()
        
        # Save to instance folder
        instance_path = Path(__file__).parent.parent.parent / 'instance' / 'uploads'
        instance_path.mkdir(parents=True, exist_ok=True)
        icon_filename = f'app_{app_id}_icon.png'
        icon_path = instance_path / icon_filename
        
        # Save the icon
        with open(icon_path, 'wb') as f:
            f.write(icon_response.content)
        
        # Update app icon path
        app.icon_path = f'uploads/{icon_filename}'
        db.session.commit()
        
        flash('Icon fetched and saved successfully!', 'success')
    except requests.RequestException as e:
        flash(f'Error fetching icon: {str(e)}', 'error')
    except Exception as e:
        flash(f'Error processing icon: {str(e)}', 'error')
    
    return redirect(url_for('admin.edit_app', app_id=app_id))

@bp.route('/apps/<int:app_id>/delete', methods=['POST'])
@login_required
@require_admin
def delete_app(app_id):
    """Delete app."""
    app = App.query.get_or_404(app_id)
    
    # Don't allow deleting the Feature Requestor app
    if app.app_name == 'feature-requestor':
        flash('Cannot delete the Feature Requestor app.', 'error')
        return redirect(url_for('admin.apps'))
    
    db.session.delete(app)
    db.session.commit()
    
    flash('App deleted successfully!', 'success')
    return redirect(url_for('admin.apps'))

@bp.route('/email-config', methods=['GET', 'POST'])
@login_required
@require_admin
def email_config():
    """Email configuration page."""
    if request.method == 'POST':
        config = {
            'from_email_mask': request.form.get('from_email_mask'),
            'smtp_host': request.form.get('smtp_host'),
            'smtp_port': int(request.form.get('smtp_port', 587)),
            'smtp_security': request.form.get('smtp_security', 'TLS'),
            'smtp_username': request.form.get('smtp_username'),
            'smtp_password': request.form.get('smtp_password')
        }
        
        if save_email_config(config):
            flash('Email configuration saved!', 'success')
        else:
            flash('Error saving email configuration.', 'error')
        
        return redirect(url_for('admin.email_config'))
    
    config = load_email_config()
    templates = load_email_templates()
    return render_template('admin/email_config.html', config=config, templates=templates)

@bp.route('/email-config/test', methods=['POST'])
@login_required
@require_admin
def test_email():
    """Test email sending."""
    test_email_address = request.form.get('test_email')
    
    if not test_email_address:
        return jsonify({'success': False, 'message': 'Email address required'}), 400
    
    success = send_email(
        to_email=test_email_address,
        subject='Test Email from Feature Requestor',
        body_html='<p>This is a test email from Feature Requestor.</p>',
        body_text='This is a test email from Feature Requestor.'
    )
    
    if success:
        return jsonify({'success': True, 'message': 'Test email sent successfully!'})
    else:
        return jsonify({'success': False, 'message': 'Failed to send test email. Check your configuration.'}), 500

@bp.route('/stripe-config', methods=['GET', 'POST'])
@login_required
@require_admin
def stripe_config():
    """Stripe configuration page."""
    if request.method == 'POST':
        config = {
            'stripe_public_key': request.form.get('stripe_public_key', '').strip(),
            'stripe_secret_key': request.form.get('stripe_secret_key', '').strip(),
            'stripe_client_id': request.form.get('stripe_client_id', '').strip(),
            'stripe_webhook_secret': request.form.get('stripe_webhook_secret', '').strip()
        }
        
        if save_stripe_config(config):
            flash('Stripe configuration saved! Note: Environment variables take precedence over this configuration.', 'success')
        else:
            flash('Error saving Stripe configuration.', 'error')
        
        return redirect(url_for('admin.stripe_config'))
    
    config = load_stripe_config()
    # Check if environment variables are set (they take precedence)
    import os
    has_env_vars = bool(os.environ.get('STRIPE_SECRET_KEY') or os.environ.get('STRIPE_PUBLIC_KEY'))
    
    return render_template('admin/stripe_config.html', config=config, has_env_vars=has_env_vars)

@bp.route('/email-templates', methods=['GET', 'POST'])
@login_required
@require_admin
def email_templates():
    """Email templates management page."""
    if request.method == 'POST':
        templates = request.get_json()
        if save_email_templates(templates):
            return jsonify({'success': True})
        return jsonify({'success': False}), 500
    
    templates = load_email_templates()
    return render_template('admin/email_templates.html', templates=templates)

@bp.route('/email-templates/test', methods=['POST'])
@login_required
@require_admin
def test_template_email():
    """Send test email for a specific template."""
    data = request.get_json()
    template_name = data.get('template_name')
    user_id = data.get('user_id')
    
    if not template_name or not user_id:
        return jsonify({'success': False, 'message': 'Template name and user ID required'}), 400
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    # Load templates
    templates = load_email_templates()
    template = templates.get(template_name)
    
    if not template:
        return jsonify({'success': False, 'message': 'Template not found'}), 404
    
    # Prepare variables for template substitution
    from app.utils.email import substitute_template_variables
    
    # Get base URL for links
    base_url = request.host_url.rstrip('/')
    
    # Prepare variables based on template type
    variables = {
        'user_name': user.name,
        'verification_link': f'{base_url}/auth/verify-email?token=test_token',
        'reset_link': f'{base_url}/auth/reset-password?token=test_token',
        'app_name': 'Test App',
        'feature_request_title': 'Test Feature Request',
        'feature_request_description': 'This is a test feature request description.',
        'feature_request_link': f'{base_url}/feature-requests/1',
        'message_content': 'This is a test message.',
        'message_link': f'{base_url}/messages/1',
        'new_email': user.email
    }
    
    # Substitute variables in subject and body
    subject = substitute_template_variables(template.get('subject', ''), variables)
    body = substitute_template_variables(template.get('body', ''), variables)
    
    # Send email
    success = send_email(user.email, subject, body, body)
    
    if success:
        return jsonify({'success': True, 'message': f'Test email sent to {user.email}!'})
    else:
        return jsonify({'success': False, 'message': 'Failed to send test email. Check your email configuration.'}), 500

@bp.route('/users/list', methods=['GET'])
@login_required
@require_admin
def users_list():
    """Get list of users for dropdown (JSON)."""
    users = User.query.all()
    users_data = [{
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'username': user.username
    } for user in users]
    return jsonify({'users': users_data})

@bp.route('/branding', methods=['GET', 'POST'])
@login_required
@require_admin
def branding():
    """Branding management page."""
    instance_path = Path(__file__).parent.parent.parent / 'instance'
    
    if request.method == 'POST':
        if 'icon' in request.files:
            file = request.files['icon']
            if file and file.filename:
                try:
                    icon_path = instance_path / 'icon.png'
                    file.save(icon_path)
                    flash('Icon uploaded successfully!', 'success')
                except Exception as e:
                    flash(f'Error uploading icon: {str(e)}', 'error')
        
        return redirect(url_for('admin.branding'))
    
    # Check if icon exists
    icon_path = instance_path / 'icon.png'
    has_icon = icon_path.exists()
    
    return render_template('admin/branding.html', has_icon=has_icon)

@bp.route('/database')
@login_required
@require_admin
def database():
    """Database management page."""
    return render_template('admin/database.html')

@bp.route('/data-viewer')
@login_required
@require_admin
def data_viewer():
    """View raw database tables (admin only, with masked sensitive data)."""
    table_name = request.args.get('table', '')
    
    # Get all table names
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    all_tables = inspector.get_table_names()
    
    table_data = None
    columns = []
    
    if table_name and table_name in all_tables:
        # Get table columns
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        
        # Get table data (limit to 100 rows for performance)
        result = db.session.execute(db.text(f'SELECT * FROM {table_name} LIMIT 100'))
        rows = result.fetchall()
        
        # Convert to list of dicts and mask sensitive data
        sensitive_fields = ['password_hash', 'stripe_account_id', 'token', 'password']
        table_data = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            # Mask sensitive fields
            for field in sensitive_fields:
                if field in row_dict and row_dict[field]:
                    row_dict[field] = '***'
            table_data.append(row_dict)
    
    return render_template('admin/data_viewer.html', 
                         all_tables=all_tables, 
                         current_table=table_name,
                         table_data=table_data,
                         columns=columns)

@bp.route('/feature-requests/<int:request_id>/remove-developer/<int:developer_id>', methods=['GET', 'POST'])
@login_required
@require_admin
def remove_developer_from_request(request_id, developer_id):
    """Admin remove developer from feature request."""
    from app.models import FeatureRequestDeveloper, FeatureRequestDeveloperHistory, Notification
    
    feature_request = FeatureRequest.query.get_or_404(request_id)
    developer = User.query.get_or_404(developer_id)
    
    if request.method == 'POST':
        reason = request.form.get('reason', '')
        
        # Find the developer relationship
        dev_entry = FeatureRequestDeveloper.query.filter_by(
            feature_request_id=request_id,
            developer_id=developer_id,
            removed_at=None
        ).first()
        
        if not dev_entry:
            flash('Developer is not currently working on this request.', 'error')
            return redirect(url_for('feature_requests.detail', request_id=request_id))
        
        # Record removal
        dev_entry.removed_at = datetime.utcnow()
        db.session.commit()
        
        # Add to history
        history_entry = FeatureRequestDeveloperHistory(
            feature_request_id=request_id,
            developer_id=developer_id,
            started_at=dev_entry.added_at,
            removed_at=datetime.utcnow(),
            removed_by='admin'
        )
        db.session.add(history_entry)
        
        # If no other developers, set status back to 'requested'
        remaining_devs = FeatureRequestDeveloper.query.filter_by(
            feature_request_id=request_id,
            removed_at=None
        ).count()
        if remaining_devs == 0 and feature_request.status == 'in_progress':
            feature_request.status = 'requested'
            feature_request.projected_completion_date = None
        
        # Create notification for developer - store data instead of message
        notification_data = {
            'feature_request_id': request_id,
            'reason': reason if reason else None
        }
        
        notification = Notification(
            user_id=developer_id,
            notification_type='developer_removed',
            notification_message=''  # Empty string for backward compatibility with NOT NULL constraint
        )
        notification.set_data(notification_data)
        db.session.add(notification)
        
        db.session.commit()
        
        flash(f'Developer {developer.name} has been removed from the request.', 'success')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    return render_template('admin/remove_developer.html', 
                         feature_request=feature_request, 
                         developer=developer)

@bp.route('/database/backup', methods=['POST'])
@login_required
@require_admin
def backup_database():
    """Create database backup."""
    instance_path = Path(__file__).parent.parent.parent / 'instance'
    db_path = instance_path / 'data' / 'feature_requestor.db'
    backup_path = instance_path / 'data' / f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    
    if db_path.exists():
        shutil.copy2(db_path, backup_path)
        return send_file(str(backup_path), as_attachment=True, download_name=f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
    
    flash('Database file not found.', 'error')
    return redirect(url_for('admin.database'))

@bp.route('/database/restore', methods=['POST'])
@login_required
@require_admin
def restore_database():
    """Restore database from uploaded backup."""
    if 'backup_file' not in request.files:
        flash('No backup file provided.', 'error')
        return redirect(url_for('admin.database'))
    
    file = request.files['backup_file']
    if not file or not file.filename:
        flash('No file selected.', 'error')
        return redirect(url_for('admin.database'))
    
    if not file.filename.endswith('.db'):
        flash('Invalid file type. Please upload a .db file.', 'error')
        return redirect(url_for('admin.database'))
    
    try:
        instance_path = Path(__file__).parent.parent.parent / 'instance'
        db_path = instance_path / 'data' / 'feature_requestor.db'
        
        # Create backup of current database before restore
        if db_path.exists():
            current_backup = instance_path / 'data' / f'pre_restore_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
            shutil.copy2(db_path, current_backup)
        
        # Save uploaded file
        file.save(str(db_path))
        
        flash('Database restored successfully! A backup of the previous database was created.', 'success')
    except Exception as e:
        flash(f'Error restoring database: {str(e)}', 'error')
    
    return redirect(url_for('admin.database'))

@bp.route('/database/generate-test-data', methods=['POST'])
@login_required
@require_admin
def generate_test_data():
    """Generate test data for development and testing."""
    try:
        from app.utils.test_data import generate_test_data as gen_test_data
        counts = gen_test_data()
        
        summary = []
        for key, value in counts.items():
            if value > 0:
                summary.append(f"{value} {key}")
        
        flash(f'Test data generated successfully! Created: {", ".join(summary)}', 'success')
    except Exception as e:
        flash(f'Error generating test data: {str(e)}', 'error')
    
    return redirect(url_for('admin.database'))

@bp.route('/database/clear-test-data', methods=['POST'])
@login_required
@require_admin
def clear_test_data():
    """Clear all test data generated by generate_test_data()."""
    try:
        from app.utils.test_data import clear_test_data as clear_test
        counts = clear_test()
        
        summary = []
        for key, value in counts.items():
            if value > 0:
                summary.append(f"{value} {key}")
        
        if summary:
            flash(f'Test data cleared successfully! Deleted: {", ".join(summary)}', 'success')
        else:
            flash('No test data found to clear.', 'info')
    except Exception as e:
        flash(f'Error clearing test data: {str(e)}', 'error')
    
    return redirect(url_for('admin.database'))

@bp.route('/database/fix', methods=['POST'])
@login_required
@require_admin
def fix_database():
    """Run database initialization to apply migrations and fix schema."""
    try:
        from app.utils.db_init import init_db
        init_db()
        flash('Database fixed successfully! All migrations have been applied.', 'success')
    except Exception as e:
        flash(f'Error fixing database: {str(e)}', 'error')
    
    return redirect(url_for('admin.database'))

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
@require_admin
def settings():
    """Application settings page."""
    if request.method == 'POST':
        config = {
            'confirmation_percentage': int(request.form.get('confirmation_percentage', 80)),
            'similar_request_max_results': int(request.form.get('similar_request_max_results', 5)),
            'similar_request_threshold': float(request.form.get('similar_request_threshold', 0.6))
        }
        
        if save_config(config):
            flash('Settings saved!', 'success')
        else:
            flash('Error saving settings.', 'error')
        
        return redirect(url_for('admin.settings'))
    
    config = load_config()
    return render_template('admin/settings.html', config=config)

@bp.route('/users/<int:user_id>/view-as', methods=['POST'])
@login_required
def view_as_user(user_id):
    """Start viewing the site as another user."""
    # Get the actual admin user (not the viewed user if already in view-as mode)
    actual_admin_id = session.get('actual_admin_id')
    
    # If not in view-as mode, check if current user is admin
    if not actual_admin_id:
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Only admins can use view as feature.', 'error')
            return redirect(url_for('home.dashboard'))
        actual_admin_id = current_user.id
    else:
        # Verify the actual admin is still an admin
        actual_admin = User.query.get(actual_admin_id)
        if not actual_admin or actual_admin.role != 'admin':
            flash('Only admins can use view as feature.', 'error')
            session.pop('actual_admin_id', None)
            session.pop('view_as_user_id', None)
            return redirect(url_for('home.dashboard'))
    
    # Get target user
    target_user = User.query.get_or_404(user_id)
    
    # Store the actual admin ID in session
    session['actual_admin_id'] = actual_admin_id
    session['view_as_user_id'] = target_user.id
    
    # Log in as the target user
    login_user(target_user, remember=False)
    
    flash(f'Now viewing as {target_user.name} ({target_user.username}). Sensitive information is masked.', 'info')
    return redirect(url_for('home.dashboard'))

@bp.route('/exit-view-as', methods=['POST'])
@login_required
def exit_view_as():
    """Exit view as mode and return to admin account."""
    actual_admin_id = session.get('actual_admin_id')
    
    if not actual_admin_id:
        flash('Not in view as mode.', 'info')
        return redirect(url_for('home.dashboard'))
    
    # Get the actual admin user
    actual_admin = User.query.get(actual_admin_id)
    
    if not actual_admin:
        flash('Admin account not found.', 'error')
        session.pop('actual_admin_id', None)
        session.pop('view_as_user_id', None)
        return redirect(url_for('auth.login'))
    
    # Verify the admin is still an admin
    if actual_admin.role != 'admin':
        flash('Admin account no longer has admin privileges.', 'error')
        session.pop('actual_admin_id', None)
        session.pop('view_as_user_id', None)
        return redirect(url_for('auth.login'))
    
    # Clear view as session data
    session.pop('actual_admin_id', None)
    session.pop('view_as_user_id', None)
    
    # Log back in as admin
    login_user(actual_admin, remember=False)
    
    flash('Returned to admin account.', 'success')
    return redirect(url_for('admin.users'))


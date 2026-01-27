# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Flask application initialization.
See instructions/architecture for development guidelines.
"""

from flask import Flask, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix
import os
from pathlib import Path

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_name='default'):
    """
    Application factory pattern for creating Flask app instances.
    
    Args:
        config_name: Configuration name to use (default, development, production)
    
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Get instance folder path
    instance_path = Path(__file__).parent.parent / 'instance'
    instance_path.mkdir(exist_ok=True)
    (instance_path / 'data').mkdir(exist_ok=True)
    (instance_path / 'uploads').mkdir(exist_ok=True)
    app.instance_path = str(instance_path)
    
    # Configure app
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{instance_path}/data/feature_requestor.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # CRITICAL: Configure ProxyFix BEFORE extensions and routes
    # This allows the app to work properly when proxied by AppManager
    # ProxyFix is safe to use even when not behind a proxy - it only processes
    # X-Forwarded-* headers if they're present. If not present, requests pass through unchanged.
    try:
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=1,      # Number of proxies in front (AppManager = 1)
            x_proto=1,    # Trust X-Forwarded-Proto header
            x_host=1,     # Trust X-Forwarded-Host header
            x_port=1,     # Trust X-Forwarded-Port header
            x_prefix=1    # Trust X-Forwarded-Prefix header
        )
    except ImportError:
        # ProxyFix not available (older Werkzeug version)
        # App will still work, but may not properly handle reverse proxy headers
        import warnings
        warnings.warn("werkzeug.middleware.proxy_fix not available. Install werkzeug>=0.15.0 for proxy support.")
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        from flask import session
        # Check if we're in view-as mode
        view_as_user_id = session.get('view_as_user_id')
        if view_as_user_id:
            # Return the user being viewed
            try:
                return User.query.get(int(view_as_user_id))
            except (ValueError, TypeError):
                return None
        
        # Handle user_id - it should be numeric, but handle edge cases
        try:
            # Try to convert to int (normal case)
            user_id_int = int(user_id)
            return User.query.get(user_id_int)
        except (ValueError, TypeError):
            # If user_id is not numeric (e.g., username string), try to find by username
            # This can happen if session cookies get corrupted or mixed between apps
            try:
                return User.query.filter_by(username=str(user_id)).first()
            except Exception:
                return None
    
    # Register blueprints
    from app.routes import auth, api, feature_requests, apps, home, messages, admin, stripe, account, receipts, quiz, rules, notifications
    app.register_blueprint(auth.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(feature_requests.bp)
    app.register_blueprint(apps.bp)
    app.register_blueprint(home.bp)
    app.register_blueprint(messages.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(stripe.bp)
    app.register_blueprint(account.bp)
    app.register_blueprint(receipts.bp)
    app.register_blueprint(quiz.bp)
    app.register_blueprint(rules.bp)
    app.register_blueprint(notifications.bp)
    
    # Register template filters and globals
    from app.utils.currency import convert_currency, format_currency
    app.jinja_env.filters['convert_currency'] = convert_currency
    app.jinja_env.filters['format_currency'] = format_currency
    app.jinja_env.globals['convert_currency'] = convert_currency
    app.jinja_env.globals['format_currency'] = format_currency
    
    # URL formatting filter
    @app.template_filter('format_url')
    def format_url(url):
        """Format URL by stripping whitespace and adding protocol if missing."""
        if not url:
            return None
        url = url.strip()
        if not url:
            return None
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    
    # Mask sensitive data filter
    @app.template_filter('mask_sensitive')
    def mask_sensitive(value):
        """Mask sensitive data when in view-as mode."""
        from flask import session
        if session.get('view_as_user_id') and value:
            # Mask the value, showing only first 4 and last 4 characters if long enough
            if isinstance(value, str):
                if len(value) > 8:
                    return value[:4] + '****' + value[-4:]
                elif len(value) > 0:
                    # For shorter strings, just show asterisks
                    return '****'
            return '****'
        return value
    
    # Context processor for icon URL
    @app.context_processor
    def inject_icon_url():
        """Make icon URL available to all templates."""
        from flask import session
        from flask_login import current_user
        icon_path = instance_path / 'icon.png'
        has_icon = icon_path.exists()
        
        # Check if admin is in view-as mode
        is_view_as_mode = bool(session.get('view_as_user_id'))
        actual_admin_id = session.get('actual_admin_id')
        actual_admin = None
        if actual_admin_id:
            from app.models import User
            actual_admin = User.query.get(actual_admin_id)
        
        # Get unread notification count (excluding message notifications)
        unread_notification_count = 0
        unread_message_count = 0
        if current_user.is_authenticated:
            from app.models import Notification, MessageThreadParticipant, Message
            # Count unread notifications excluding message notification types
            unread_notification_count = Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).filter(
                Notification.notification_type != 'new_message',
                Notification.notification_type != 'message_received'
            ).count()
            
            # Count unread messages
            # Get all threads user is in
            user_participants = MessageThreadParticipant.query.filter_by(
                user_id=current_user.id,
                is_blocked=False
            ).all()
            
            for participant in user_participants:
                # Count messages created after last_read_at
                if participant.last_read_at:
                    unread_messages = Message.query.filter(
                        Message.thread_id == participant.thread_id,
                        Message.sender_id != current_user.id,
                        Message.created_at > participant.last_read_at
                    ).count()
                else:
                    # If never read, count all messages not from user
                    unread_messages = Message.query.filter(
                        Message.thread_id == participant.thread_id,
                        Message.sender_id != current_user.id
                    ).count()
                unread_message_count += unread_messages
        
        return {
            'has_custom_icon': has_icon,
            'icon_url': url_for('admin.serve_icon') if has_icon else None,
            'is_view_as_mode': is_view_as_mode,
            'actual_admin': actual_admin,
            'unread_notification_count': unread_notification_count,
            'unread_message_count': unread_message_count
        }
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {'error': 'Internal server error'}, 500
    
    # Create database tables
    with app.app_context():
        from app.utils.db_init import init_db
        init_db()
    
    # Initialize notification scheduler
    from app.utils.notification_scheduler import init_scheduler
    init_scheduler(app)
    
    return app


# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Database initialization and setup.
See instructions/architecture for development guidelines.
"""

from app import db
from app.models import User, App
from app.utils.auth import hash_password, generate_username
import os

def init_db():
    """
    Initialize the database with all tables and create default admin account.
    Creates the Feature Requestor app automatically on first launch.
    """
    # Import all models to ensure they're registered
    from app.models import (
        User, App, FeatureRequest, Comment,
        FeatureRequestDeveloper, FeatureRequestDeveloperHistory,
        PaymentRatio, PaymentRatioMessage, PaymentTransaction,
        MessageThread, MessageThreadParticipant, Message, MessagePollVote,
        Notification, NotificationPreference,
        UserSignupRequest, RoleChangeRequest, UserBlock, EmailVerificationToken
    )
    
    # Create all tables
    db.create_all()
    
    # Add creator_id column if it doesn't exist (for existing databases)
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if inspector.has_table('feature_requests'):
            columns = [col['name'] for col in inspector.get_columns('feature_requests')]
            if 'creator_id' not in columns:
                # Add the column using raw SQL
                db.session.execute(text('ALTER TABLE feature_requests ADD COLUMN creator_id INTEGER REFERENCES users(id)'))
                db.session.commit()
    except Exception as e:
        # Column might already exist or there was an error
        db.session.rollback()
        pass
    
    # Add username column to users table if it doesn't exist (migration for existing databases)
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if inspector.has_table('users'):
            columns = [col['name'] for col in inspector.get_columns('users')]
            if 'username' not in columns:
                # Add username column (nullable first, then we'll populate it)
                db.session.execute(text('ALTER TABLE users ADD COLUMN username TEXT'))
                db.session.commit()
            
            # Generate usernames for any users that don't have one (including newly added column)
            # Use raw SQL to check for NULL usernames since SQLAlchemy might not handle this well
            result = db.session.execute(text("SELECT id, name, email FROM users WHERE username IS NULL OR username = ''"))
            users_without_username = result.fetchall()
            
            for user_row in users_without_username:
                user_id, name, email = user_row
                username = generate_username(name, email)
                db.session.execute(text("UPDATE users SET username = :username WHERE id = :user_id"), 
                                 {"username": username, "user_id": user_id})
            db.session.commit()
    except Exception as e:
        # Column might already exist or there was an error
        db.session.rollback()
        pass
    
    # Add username column to user_signup_requests table if it doesn't exist
    try:
        from sqlalchemy import inspect, text
        from app.models import UserSignupRequest
        inspector = inspect(db.engine)
        if inspector.has_table('user_signup_requests'):
            columns = [col['name'] for col in inspector.get_columns('user_signup_requests')]
            if 'username' not in columns:
                # Add username column
                db.session.execute(text('ALTER TABLE user_signup_requests ADD COLUMN username TEXT'))
                db.session.commit()
            
            # Generate usernames for any signup requests that don't have one
            result = db.session.execute(text("SELECT id, name, email FROM user_signup_requests WHERE username IS NULL OR username = ''"))
            requests_without_username = result.fetchall()
            
            for request_row in requests_without_username:
                request_id, name, email = request_row
                username = generate_username(name, email)
                db.session.execute(text("UPDATE user_signup_requests SET username = :username WHERE id = :request_id"), 
                                 {"username": username, "request_id": request_id})
            db.session.commit()
    except Exception as e:
        # Column might already exist or there was an error
        db.session.rollback()
        pass
    
    # Add is_test_data column to users table if it doesn't exist (migration for existing databases)
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if inspector.has_table('users'):
            columns = [col['name'] for col in inspector.get_columns('users')]
            if 'is_test_data' not in columns:
                # Add is_test_data column with default value False
                db.session.execute(text('ALTER TABLE users ADD COLUMN is_test_data BOOLEAN NOT NULL DEFAULT 0'))
                db.session.commit()
    except Exception as e:
        # Column might already exist or there was an error
        db.session.rollback()
        pass
    
    # Add bid_currency column to comments table if it doesn't exist (migration for existing databases)
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if inspector.has_table('comments'):
            columns = [col['name'] for col in inspector.get_columns('comments')]
            if 'bid_currency' not in columns:
                # Add bid_currency column (nullable for old bids)
                db.session.execute(text('ALTER TABLE comments ADD COLUMN bid_currency TEXT'))
                db.session.commit()
    except Exception as e:
        # Column might already exist or there was an error
        db.session.rollback()
        pass
    
    # Comprehensive column migration check for all tables
    # This ensures all tables have all required columns from the models
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        
        # Check users table for preferred_currency (if it was added later)
        if inspector.has_table('users'):
            columns = [col['name'] for col in inspector.get_columns('users')]
            if 'preferred_currency' not in columns:
                db.session.execute(text("ALTER TABLE users ADD COLUMN preferred_currency TEXT NOT NULL DEFAULT 'CAD'"))
                db.session.commit()
        
        # Check feature_requests table for all columns
        if inspector.has_table('feature_requests'):
            columns = [col['name'] for col in inspector.get_columns('feature_requests')]
            if 'projected_completion_date' not in columns:
                db.session.execute(text('ALTER TABLE feature_requests ADD COLUMN projected_completion_date DATETIME'))
                db.session.commit()
            if 'delivered_date' not in columns:
                db.session.execute(text('ALTER TABLE feature_requests ADD COLUMN delivered_date DATETIME'))
                db.session.commit()
            if 'total_bid_amount' not in columns:
                db.session.execute(text("ALTER TABLE feature_requests ADD COLUMN total_bid_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00"))
                db.session.commit()
        
        # Check comments table for all columns
        if inspector.has_table('comments'):
            columns = [col['name'] for col in inspector.get_columns('comments')]
            if 'is_edited' not in columns:
                db.session.execute(text('ALTER TABLE comments ADD COLUMN is_edited BOOLEAN NOT NULL DEFAULT 0'))
                db.session.commit()
            if 'is_deleted' not in columns:
                db.session.execute(text('ALTER TABLE comments ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT 0'))
                db.session.commit()
            if 'original_comment' not in columns:
                db.session.execute(text('ALTER TABLE comments ADD COLUMN original_comment TEXT'))
                db.session.commit()
        
        # Check payment_transactions table for currency and is_guest_transaction
        if inspector.has_table('payment_transactions'):
            columns = [col['name'] for col in inspector.get_columns('payment_transactions')]
            if 'currency' not in columns:
                db.session.execute(text("ALTER TABLE payment_transactions ADD COLUMN currency TEXT NOT NULL DEFAULT 'CAD'"))
                db.session.commit()
            if 'is_guest_transaction' not in columns:
                db.session.execute(text('ALTER TABLE payment_transactions ADD COLUMN is_guest_transaction BOOLEAN NOT NULL DEFAULT 0'))
                db.session.commit()
            if 'guest_email' not in columns:
                db.session.execute(text('ALTER TABLE payment_transactions ADD COLUMN guest_email TEXT'))
                db.session.commit()
            if 'transaction_date' not in columns:
                # SQLite doesn't support DEFAULT CURRENT_TIMESTAMP in ALTER TABLE, so we add it nullable first
                db.session.execute(text('ALTER TABLE payment_transactions ADD COLUMN transaction_date DATETIME'))
                # Then update existing rows to have a default value
                db.session.execute(text("UPDATE payment_transactions SET transaction_date = created_at WHERE transaction_date IS NULL"))
                db.session.commit()
        
        # Check notifications table for read_at, notification_data, and nullable notification_message
        if inspector.has_table('notifications'):
            columns = [col['name'] for col in inspector.get_columns('notifications')]
            if 'read_at' not in columns:
                db.session.execute(text('ALTER TABLE notifications ADD COLUMN read_at DATETIME'))
                db.session.commit()
            if 'notification_data' not in columns:
                db.session.execute(text('ALTER TABLE notifications ADD COLUMN notification_data TEXT'))
                db.session.commit()
            # Make notification_message nullable (SQLite doesn't support ALTER COLUMN, but we can check if it's already nullable)
            # For SQLite, we'll just ensure the column exists and is nullable in the model
            # The model already has nullable=True, so new tables will be correct
        
        # Check notification_preferences table for custom_rule
        if inspector.has_table('notification_preferences'):
            columns = [col['name'] for col in inspector.get_columns('notification_preferences')]
            if 'custom_rule' not in columns:
                db.session.execute(text('ALTER TABLE notification_preferences ADD COLUMN custom_rule TEXT'))
                db.session.commit()
        
        # Check feature_request_developers table for removed_at
        if inspector.has_table('feature_request_developers'):
            columns = [col['name'] for col in inspector.get_columns('feature_request_developers')]
            if 'removed_at' not in columns:
                db.session.execute(text('ALTER TABLE feature_request_developers ADD COLUMN removed_at DATETIME'))
                db.session.commit()
            if 'is_approved' not in columns:
                db.session.execute(text('ALTER TABLE feature_request_developers ADD COLUMN is_approved BOOLEAN NOT NULL DEFAULT 0'))
                db.session.commit()
            if 'approved_by_id' not in columns:
                db.session.execute(text('ALTER TABLE feature_request_developers ADD COLUMN approved_by_id INTEGER REFERENCES users(id)'))
                db.session.commit()
        
        # Check message_threads table for thread_type
        if inspector.has_table('message_threads'):
            columns = [col['name'] for col in inspector.get_columns('message_threads')]
            if 'thread_type' not in columns:
                db.session.execute(text("ALTER TABLE message_threads ADD COLUMN thread_type TEXT NOT NULL DEFAULT 'direct'"))
                db.session.commit()
        
        # Check messages table for is_poll, poll_type, and poll_target_user_id
        if inspector.has_table('messages'):
            columns = [col['name'] for col in inspector.get_columns('messages')]
            if 'is_poll' not in columns:
                db.session.execute(text('ALTER TABLE messages ADD COLUMN is_poll BOOLEAN NOT NULL DEFAULT 0'))
                db.session.commit()
            if 'poll_type' not in columns:
                db.session.execute(text('ALTER TABLE messages ADD COLUMN poll_type TEXT'))
                db.session.commit()
            if 'poll_target_user_id' not in columns:
                db.session.execute(text('ALTER TABLE messages ADD COLUMN poll_target_user_id INTEGER REFERENCES users(id)'))
                db.session.commit()
        
        # Check message_thread_participants table for is_blocked and last_read_at
        if inspector.has_table('message_thread_participants'):
            columns = [col['name'] for col in inspector.get_columns('message_thread_participants')]
            if 'is_blocked' not in columns:
                db.session.execute(text('ALTER TABLE message_thread_participants ADD COLUMN is_blocked BOOLEAN NOT NULL DEFAULT 0'))
                db.session.commit()
            if 'last_read_at' not in columns:
                db.session.execute(text('ALTER TABLE message_thread_participants ADD COLUMN last_read_at DATETIME'))
                db.session.commit()
            if 'joined_at' not in columns:
                # SQLite doesn't support DEFAULT CURRENT_TIMESTAMP in ALTER TABLE, so we add it nullable first
                db.session.execute(text('ALTER TABLE message_thread_participants ADD COLUMN joined_at DATETIME'))
                # Then update existing rows to have a default value
                db.session.execute(text("UPDATE message_thread_participants SET joined_at = datetime('now') WHERE joined_at IS NULL"))
                db.session.commit()
        
        # Check email_verification_tokens table for all columns
        if inspector.has_table('email_verification_tokens'):
            columns = [col['name'] for col in inspector.get_columns('email_verification_tokens')]
            if 'signup_request_id' not in columns:
                db.session.execute(text('ALTER TABLE email_verification_tokens ADD COLUMN signup_request_id INTEGER REFERENCES user_signup_requests(id)'))
                db.session.commit()
            if 'old_email' not in columns:
                db.session.execute(text('ALTER TABLE email_verification_tokens ADD COLUMN old_email TEXT'))
                db.session.commit()
            if 'verification_type' not in columns:
                db.session.execute(text("ALTER TABLE email_verification_tokens ADD COLUMN verification_type TEXT NOT NULL DEFAULT 'signup'"))
                db.session.commit()
            if 'expires_at' not in columns:
                db.session.execute(text('ALTER TABLE email_verification_tokens ADD COLUMN expires_at DATETIME NOT NULL'))
                db.session.commit()
            if 'verified_at' not in columns:
                db.session.execute(text('ALTER TABLE email_verification_tokens ADD COLUMN verified_at DATETIME'))
                db.session.commit()
        
    except Exception as e:
        # Column might already exist or there was an error
        db.session.rollback()
        pass
    
    # Create default admin account if it doesn't exist
    admin_username = os.environ.get('ADMIN_USERNAME', 'LastTerminal')
    admin_email = 'admin@feature-requestor.com'
    
    # First check by username
    admin = User.query.filter_by(username=admin_username).first()
    
    # If not found by username, check by email (for existing databases)
    if not admin:
        admin = User.query.filter_by(email=admin_email).first()
        # If found by email, update the username
        if admin:
            admin.username = admin_username
            db.session.commit()
    
    # Only create new admin if neither username nor email exists
    if not admin:
        # Default admin credentials from deploy config
        admin_password = os.environ.get('ADMIN_PASSWORD', 'WhiteMage')
        
        admin = User(
            username=admin_username,
            name='Admin',
            email=admin_email,
            password_hash=hash_password(admin_password),
            email_verified=True,
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
    
    # Create Feature Requestor app if it doesn't exist
    feature_requestor_app = App.query.filter_by(app_name='feature-requestor').first()
    if not feature_requestor_app:
        feature_requestor_app = App(
            app_name='feature-requestor',
            app_display_name='Feature Requestor',
            app_description='The Feature Requestor application itself - request features for this platform!',
            app_url='',
            github_url='',
            app_owner_id=admin.id
        )
        db.session.add(feature_requestor_app)
        db.session.commit()


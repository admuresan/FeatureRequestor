# IMPORTANT: Read instructions/architecture before making changes to this file
"""
User model for storing user account information.
See instructions/architecture for development guidelines.
"""

from app import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    """User account model."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.Text, nullable=False, unique=True)
    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    role = db.Column(db.Text, nullable=False)  # 'requester', 'dev', or 'admin'
    stripe_account_id = db.Column(db.Text, nullable=True)
    stripe_account_status = db.Column(db.Text, nullable=True)  # 'connected', 'pending', 'disconnected', or NULL
    preferred_currency = db.Column(db.Text, nullable=False, default='CAD')  # 'CAD', 'USD', 'EUR'
    is_test_data = db.Column(db.Boolean, nullable=False, default=False)  # Flag to mark test data
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    comments = db.relationship('Comment', backref='commenter', lazy='dynamic', foreign_keys='Comment.commenter_id')
    feature_requests_created = db.relationship('FeatureRequest', backref='creator', lazy='dynamic', foreign_keys='FeatureRequest.creator_id', overlaps='creator')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def get_id(self):
        """Required by Flask-Login."""
        return str(self.id)


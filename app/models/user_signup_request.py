# IMPORTANT: Read instructions/architecture before making changes to this file
"""
User Signup Request model for admin approval workflow.
See instructions/architecture for development guidelines.
"""

from app import db
from datetime import datetime

class UserSignupRequest(db.Model):
    """Sign-up request awaiting admin approval."""
    __tablename__ = 'user_signup_requests'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.Text, nullable=False, unique=True)
    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False, unique=True)
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    password_hash = db.Column(db.Text, nullable=False)
    requested_role = db.Column(db.Text, nullable=False)  # 'requester' or 'dev'
    status = db.Column(db.Text, nullable=False, default='pending')  # 'pending', 'approved', 'denied'
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    reviewed_by = db.relationship('User', backref='reviewed_signups')
    
    def __repr__(self):
        return f'<UserSignupRequest {self.username}>'


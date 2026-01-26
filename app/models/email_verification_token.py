# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Email Verification Token model.
See instructions/architecture for development guidelines.
"""

from app import db
from datetime import datetime, timedelta

class EmailVerificationToken(db.Model):
    """Email verification tokens for sign-up and email changes."""
    __tablename__ = 'email_verification_tokens'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # NULL if user not yet created
    signup_request_id = db.Column(db.Integer, db.ForeignKey('user_signup_requests.id'), nullable=True)
    email = db.Column(db.Text, nullable=False)  # Email being verified
    old_email = db.Column(db.Text, nullable=True)  # Previous email (for email changes)
    token = db.Column(db.Text, nullable=False, unique=True)  # Cryptographically secure random string
    verification_type = db.Column(db.Text, nullable=False, default='signup')  # 'signup' or 'email_change'
    expires_at = db.Column(db.DateTime, nullable=False)  # 24 hours from creation
    verified_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='verification_tokens')
    signup_request = db.relationship('UserSignupRequest', backref='verification_tokens')
    
    def is_expired(self):
        """Check if token has expired."""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """Check if token is valid (not expired and not verified)."""
        return not self.is_expired() and self.verified_at is None
    
    def __repr__(self):
        return f'<EmailVerificationToken {self.token[:8]}...>'


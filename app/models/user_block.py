# IMPORTANT: Read instructions/architecture before making changes to this file
"""
User Block model for blocking users in messaging.
See instructions/architecture for development guidelines.
"""

from app import db
from datetime import datetime

class UserBlock(db.Model):
    """User blocking relationships."""
    __tablename__ = 'user_blocks'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    blocker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    blocked_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    blocker = db.relationship('User', foreign_keys=[blocker_id], backref='blocks')
    blocked = db.relationship('User', foreign_keys=[blocked_id], backref='blocked_by')
    
    def __repr__(self):
        return f'<UserBlock {self.blocker_id}-{self.blocked_id}>'


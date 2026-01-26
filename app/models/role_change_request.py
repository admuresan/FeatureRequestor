# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Role Change Request model for requester-to-dev upgrade workflow.
See instructions/architecture for development guidelines.
"""

from app import db
from datetime import datetime

class RoleChangeRequest(db.Model):
    """Role change request for requester users wanting to upgrade to dev."""
    __tablename__ = 'role_change_requests'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    requested_role = db.Column(db.Text, nullable=False, default='dev')  # Currently only 'dev' is supported
    status = db.Column(db.Text, nullable=False, default='pending')  # 'pending', 'approved', 'denied'
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='role_change_requests')
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id], backref='reviewed_role_changes')
    
    def __repr__(self):
        return f'<RoleChangeRequest {self.user_id} -> {self.requested_role}>'


# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Feature Request Developer models for tracking developers working on requests.
See instructions/architecture for development guidelines.
"""

from app import db
from datetime import datetime

class FeatureRequestDeveloper(db.Model):
    """Many-to-many relationship between feature requests and developers."""
    __tablename__ = 'feature_request_developers'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    feature_request_id = db.Column(db.Integer, db.ForeignKey('feature_requests.id'), nullable=False)
    developer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_approved = db.Column(db.Boolean, nullable=False, default=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    added_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    removed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    developer = db.relationship('User', foreign_keys=[developer_id], backref='developer_requests')
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    
    def __repr__(self):
        return f'<FeatureRequestDeveloper {self.feature_request_id}-{self.developer_id}>'

class FeatureRequestDeveloperHistory(db.Model):
    """History of developers who previously worked on requests."""
    __tablename__ = 'feature_request_developer_history'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    feature_request_id = db.Column(db.Integer, db.ForeignKey('feature_requests.id'), nullable=False)
    developer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False)
    removed_at = db.Column(db.DateTime, nullable=False)
    removed_by = db.Column(db.Text, nullable=False)  # 'self', 'admin', or 'system'
    
    # Relationships
    developer = db.relationship('User', backref='developer_history')
    feature_request = db.relationship('FeatureRequest', backref='developer_history')
    
    def __repr__(self):
        return f'<FeatureRequestDeveloperHistory {self.id}>'


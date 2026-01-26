# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Feature Request model.
See instructions/architecture for development guidelines.
"""

from app import db
from datetime import datetime
from decimal import Decimal

class FeatureRequest(db.Model):
    """Feature request model."""
    __tablename__ = 'feature_requests'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.Text, nullable=False)
    app_id = db.Column(db.Integer, db.ForeignKey('apps.id'), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # User who created the request
    request_type = db.Column(db.Text, nullable=False)  # 'UI/UX' or 'backend'
    request_category = db.Column(db.Text, nullable=False)  # 'bug' or 'enhancement'
    status = db.Column(db.Text, nullable=False, default='requested')  # 'requested', 'in_progress', 'completed', 'confirmed', 'cancelled'
    date_requested = db.Column(db.DateTime, nullable=False)
    total_bid_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    delivered_date = db.Column(db.DateTime, nullable=True)
    projected_completion_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    # creator relationship is created via backref from User.feature_requests_created
    comments = db.relationship('Comment', backref='feature_request', lazy='dynamic', cascade='all, delete-orphan')
    developers = db.relationship('FeatureRequestDeveloper', backref='feature_request', lazy='dynamic', cascade='all, delete-orphan')
    payment_ratios = db.relationship('PaymentRatio', backref='feature_request', lazy='dynamic', cascade='all, delete-orphan')
    payment_ratio_messages = db.relationship('PaymentRatioMessage', backref='feature_request', lazy='dynamic', cascade='all, delete-orphan')
    payment_transactions = db.relationship('PaymentTransaction', backref='feature_request', lazy='dynamic')
    
    def __repr__(self):
        return f'<FeatureRequest {self.title}>'


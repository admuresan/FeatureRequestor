# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Payment ratio models for multi-dev payment distribution.
See instructions/architecture for development guidelines.
"""

from app import db
from datetime import datetime
from decimal import Decimal

class PaymentRatio(db.Model):
    """Payment ratio configuration for multi-dev feature requests."""
    __tablename__ = 'payment_ratios'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    feature_request_id = db.Column(db.Integer, db.ForeignKey('feature_requests.id'), nullable=False)
    developer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ratio_percentage = db.Column(db.Numeric(5, 2), nullable=False)  # 0.00 to 100.00
    is_accepted = db.Column(db.Boolean, nullable=False, default=False)
    accepted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    developer = db.relationship('User', backref='payment_ratios')
    
    def __repr__(self):
        return f'<PaymentRatio {self.feature_request_id}-{self.developer_id}>'

class PaymentRatioMessage(db.Model):
    """Messages in the payment ratio allocation section."""
    __tablename__ = 'payment_ratio_messages'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    feature_request_id = db.Column(db.Integer, db.ForeignKey('feature_requests.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', backref='payment_ratio_messages')
    
    def __repr__(self):
        return f'<PaymentRatioMessage {self.id}>'


# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Payment Transaction model for tracking all payments.
See instructions/architecture for development guidelines.
"""

from app import db
from datetime import datetime
from decimal import Decimal

class PaymentTransaction(db.Model):
    """Payment transaction model."""
    __tablename__ = 'payment_transactions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # NULL for guest tips
    guest_email = db.Column(db.Text, nullable=True)  # For guest transactions
    transaction_type = db.Column(db.Text, nullable=False)  # 'feature_request_payment' or 'tip'
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.Text, nullable=False)  # 'CAD', 'USD', 'EUR'
    app_id = db.Column(db.Integer, db.ForeignKey('apps.id'), nullable=True)  # Required for tips
    feature_request_id = db.Column(db.Integer, db.ForeignKey('feature_requests.id'), nullable=True)  # NULL for tips
    stripe_transaction_id = db.Column(db.Text, nullable=True)
    direction = db.Column(db.Text, nullable=False)  # 'charged' (to requester), 'paid' (to dev), 'tip'
    is_guest_transaction = db.Column(db.Boolean, nullable=False, default=False)
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='payment_transactions')
    app = db.relationship('App', backref='payment_transactions')
    
    def __repr__(self):
        return f'<PaymentTransaction {self.id}>'


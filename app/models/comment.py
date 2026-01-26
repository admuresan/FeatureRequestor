# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Comment model for feature request comments.
See instructions/architecture for development guidelines.
"""

from app import db
from datetime import datetime
from decimal import Decimal

class Comment(db.Model):
    """Comment model."""
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    feature_request_id = db.Column(db.Integer, db.ForeignKey('feature_requests.id'), nullable=False)
    commenter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    commenter_type = db.Column(db.Text, nullable=False)  # 'requester', 'dev', or 'system'
    comment = db.Column(db.Text, nullable=False)  # Rich text
    bid_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    bid_currency = db.Column(db.Text, nullable=True)  # Currency of the bid (CAD, USD, EUR) - NULL for old bids
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_edited = db.Column(db.Boolean, nullable=False, default=False)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    original_comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Comment {self.id}>'


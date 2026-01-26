# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Statistics utilities for admin dashboard.
See instructions/architecture for development guidelines.
"""

from app import db
from app.models import App, FeatureRequest, Comment, PaymentTransaction
from app.utils.currency import convert_currency
from decimal import Decimal


def get_admin_stats():
    """Get high-level statistics for admin dashboard."""
    # Number of apps managed
    num_apps = App.query.count()
    
    # Requests made (total)
    requests_made = FeatureRequest.query.count()
    
    # Requests completed (status is 'completed' or 'confirmed')
    requests_completed = FeatureRequest.query.filter(
        FeatureRequest.status.in_(['completed', 'confirmed'])
    ).count()
    
    # Tips received (converted to CAD)
    tips = PaymentTransaction.query.filter_by(
        transaction_type='tip',
        direction='tip'
    ).all()
    tips_total_cad = Decimal('0.00')
    for tip in tips:
        tip_amount_cad = convert_currency(tip.amount, tip.currency, 'CAD')
        tips_total_cad += tip_amount_cad
    
    # Bids collected (converted to CAD) - payments charged to requesters
    bids_collected = PaymentTransaction.query.filter_by(
        transaction_type='feature_request_payment',
        direction='charged'
    ).all()
    bids_collected_total_cad = Decimal('0.00')
    for bid in bids_collected:
        bid_amount_cad = convert_currency(bid.amount, bid.currency, 'CAD')
        bids_collected_total_cad += bid_amount_cad
    
    # Bids requested (total across all not completed requests, converted to CAD)
    # Get all feature requests that are not completed/confirmed
    pending_requests = FeatureRequest.query.filter(
        ~FeatureRequest.status.in_(['completed', 'confirmed'])
    ).all()
    
    bids_requested_total_cad = Decimal('0.00')
    for req in pending_requests:
        # Sum up all bid amounts from comments for this request, converting to CAD
        # Exclude deleted comments
        comments_with_bids = Comment.query.filter_by(
            feature_request_id=req.id,
            is_deleted=False
        ).filter(Comment.bid_amount > 0).all()
        
        for comment in comments_with_bids:
            # Get currency from comment, default to CAD if not set
            comment_currency = comment.bid_currency if comment.bid_currency else 'CAD'
            bid_amount_cad = convert_currency(comment.bid_amount, comment_currency, 'CAD')
            bids_requested_total_cad += bid_amount_cad
    
    return {
        'num_apps': num_apps,
        'requests_made': requests_made,
        'requests_completed': requests_completed,
        'tips_received_cad': tips_total_cad,
        'bids_collected_cad': bids_collected_total_cad,
        'bids_requested_cad': bids_requested_total_cad
    }


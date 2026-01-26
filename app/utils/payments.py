# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Payment processing utilities.
See instructions/architecture for development guidelines.
"""

import os
import stripe
from app import db
from app.models import PaymentTransaction, FeatureRequest, Comment, PaymentRatio
from app.config import get_stripe_key
from decimal import Decimal
from datetime import datetime

# Initialize Stripe - will be set in functions that need it
def init_stripe():
    """Initialize Stripe API key from config or environment."""
    stripe.api_key = get_stripe_key('stripe_secret_key')

def calculate_fee_distribution(total_bid_amount: Decimal, bids: list) -> dict:
    """
    Calculate fee distribution for requesters.
    
    Args:
        total_bid_amount: Total bid amount
        bids: List of Comment objects with bid amounts
    
    Returns:
        Dictionary mapping commenter_id to their share of fees
    """
    if total_bid_amount == 0:
        return {}
    
    # Calculate Stripe fees (2.9% + $0.30)
    stripe_fee = (total_bid_amount * Decimal('0.029')) + Decimal('0.30')
    
    # Distribute fees proportionally
    fee_distribution = {}
    for bid in bids:
        if bid.bid_amount > 0:
            ratio = bid.bid_amount / total_bid_amount
            fee_distribution[bid.commenter_id] = stripe_fee * ratio
    
    return fee_distribution

def collect_payments(feature_request_id: int) -> bool:
    """
    Collect payments from all requesters who bid on a feature request.
    
    Args:
        feature_request_id: Feature request ID
    
    Returns:
        True if all payments collected successfully, False otherwise
    """
    init_stripe()
    if not stripe.api_key:
        return False
    
    feature_request = FeatureRequest.query.get(feature_request_id)
    if not feature_request:
        return False
    
    # Get all non-zero bids
    bids = Comment.query.filter_by(
        feature_request_id=feature_request_id,
        is_deleted=False
    ).filter(Comment.bid_amount > 0).all()
    
    if not bids:
        return True  # No payments to collect
    
    # Calculate fee distribution
    total_bid = sum([bid.bid_amount for bid in bids])
    fee_distribution = calculate_fee_distribution(total_bid, bids)
    
    # Collect payment from each requester
    from app.models import User
    all_success = True
    
    for bid in bids:
        user = User.query.get(bid.commenter_id)
        if not user or not user.stripe_account_id:
            continue
        
        # Calculate total amount (bid + fees)
        total_amount = bid.bid_amount + fee_distribution.get(bid.commenter_id, Decimal('0.00'))
        
        try:
            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=int(total_amount * 100),  # Convert to cents
                currency=user.preferred_currency.lower(),
                customer=user.stripe_account_id,
                description=f"Feature request: {feature_request.title}"
            )
            
            # Confirm payment (in real implementation, this would be done via webhook)
            # For now, we'll assume payment succeeds
            
            # Record transaction
            transaction = PaymentTransaction(
                user_id=user.id,
                transaction_type='feature_request_payment',
                amount=total_amount,
                currency=user.preferred_currency,
                feature_request_id=feature_request_id,
                stripe_transaction_id=payment_intent.id,
                direction='charged'
            )
            db.session.add(transaction)
            
        except Exception as e:
            print(f"Error collecting payment from user {user.id}: {e}")
            all_success = False
    
    db.session.commit()
    return all_success

def distribute_payments(feature_request_id: int) -> bool:
    """
    Distribute payments to developers.
    
    Args:
        feature_request_id: Feature request ID
    
    Returns:
        True if all payments distributed successfully, False otherwise
    """
    init_stripe()
    if not stripe.api_key:
        return False
    
    feature_request = FeatureRequest.query.get(feature_request_id)
    if not feature_request:
        return False
    
    # Get payment ratios
    payment_ratios = PaymentRatio.query.filter_by(
        feature_request_id=feature_request_id,
        is_accepted=True
    ).all()
    
    if not payment_ratios:
        return False
    
    # Calculate total amount to distribute
    total_amount = feature_request.total_bid_amount
    
    # TODO: Determine target payout currency and convert
    # For now, use CAD as default
    
    # Distribute to each developer
    from app.models import User, FeatureRequestDeveloper
    all_success = True
    
    for ratio in payment_ratios:
        dev = User.query.get(ratio.developer_id)
        if not dev or not dev.stripe_account_id:
            continue
        
        # Calculate dev's share
        dev_share = (total_amount * ratio.ratio_percentage) / Decimal('100.00')
        
        try:
            # Create transfer to developer
            transfer = stripe.Transfer.create(
                amount=int(dev_share * 100),  # Convert to cents
                currency=dev.preferred_currency.lower(),
                destination=dev.stripe_account_id,
                description=f"Payment for feature request: {feature_request.title}"
            )
            
            # Record transaction
            transaction = PaymentTransaction(
                user_id=dev.id,
                transaction_type='feature_request_payment',
                amount=dev_share,
                currency=dev.preferred_currency,
                feature_request_id=feature_request_id,
                stripe_transaction_id=transfer.id,
                direction='paid'
            )
            db.session.add(transaction)
            
        except Exception as e:
            print(f"Error distributing payment to dev {dev.id}: {e}")
            all_success = False
    
    db.session.commit()
    return all_success


# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Home page routes.
See instructions/architecture for development guidelines.
"""

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import FeatureRequest, Comment, PaymentTransaction
from decimal import Decimal

bp = Blueprint('home', __name__)

@bp.route('/')
def index():
    """Home page - redirects based on authentication."""
    if current_user.is_authenticated:
        return redirect(url_for('home.dashboard'))
    return redirect(url_for('feature_requests.list'))

@bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard/home page."""
    # Collect to-do items
    todo_items = []
    
    # Check email verification
    if not current_user.email_verified:
        todo_items.append({
            'type': 'error',
            'title': 'Email Not Verified',
            'message': 'Your email address has not been verified. Please verify your email to use all features.',
            'action_url': url_for('account.settings'),
            'action_text': 'Go to Account Settings'
        })
    
    # Check Stripe configuration
    if not current_user.stripe_account_id:
        todo_items.append({
            'type': 'warning',
            'title': 'Stripe Not Configured',
            'message': 'You will not be able to make or receive payments without configuring Stripe. Connect your Stripe account to enable payment features.',
            'action_url': url_for('account.settings'),
            'action_text': 'Go to Account Settings'
        })
    
    # Admin-specific to-do items
    if current_user.role == 'admin':
        import os
        from app.config import load_email_config
        
        # Check email configuration
        email_config = load_email_config()
        if not email_config.get('smtp_host') or not email_config.get('smtp_username'):
            todo_items.append({
                'type': 'warning',
                'title': 'Email Configuration Not Set Up',
                'message': 'Email functionality is not configured. Users will not be able to receive verification emails or notifications. Configure SMTP settings to enable email features.',
                'action_url': url_for('admin.email_config'),
                'action_text': 'Configure Email Settings'
            })
        
        # Check Stripe API keys
        from app.config import get_stripe_key
        stripe_secret_key = get_stripe_key('stripe_secret_key')
        stripe_public_key = get_stripe_key('stripe_public_key')
        if not stripe_secret_key or not stripe_public_key:
            todo_items.append({
                'type': 'warning',
                'title': 'Stripe API Keys Not Configured',
                'message': 'Stripe API keys are not configured. Payment features will not work. Configure Stripe settings in the admin panel.',
                'action_url': url_for('admin.stripe_config'),
                'action_text': 'Configure Stripe Settings'
            })
    
    if current_user.role == 'requester':
        stats = get_requester_stats()
        stats['todo_items'] = todo_items
        return render_template('home/requester.html', stats=stats)
    elif current_user.role == 'dev':
        stats = get_developer_stats()
        
        # Check if dev has also acted as a requester
        requester_requests = FeatureRequest.query.join(Comment).filter(
            Comment.commenter_id == current_user.id,
            Comment.commenter_type == 'requester'
        ).distinct().first()
        
        has_requester_activity = requester_requests is not None
        
        if has_requester_activity:
            requester_stats = get_requester_stats()
            stats['requester_stats'] = requester_stats
        
        stats['has_requester_activity'] = has_requester_activity
        stats['todo_items'] = todo_items
        return render_template('home/developer.html', stats=stats)
    elif current_user.role == 'admin':
        from app.utils.stats import get_admin_stats
        admin_stats = get_admin_stats()
        stats = {**admin_stats}
        stats['todo_items'] = todo_items
        return render_template('home/admin.html', stats=stats)
    else:
        return redirect(url_for('feature_requests.list'))

def get_requester_stats():
    """Get statistics for requester user."""
    # Get user's feature requests
    user_requests = FeatureRequest.query.join(Comment).filter(
        Comment.commenter_id == current_user.id,
        Comment.commenter_type == 'requester'
    ).distinct().all()
    
    # Calculate stats
    total_requests = len(user_requests)
    total_bid_amount = Decimal('0.00')
    in_progress_count = 0
    in_progress_bid = Decimal('0.00')
    finished_count = 0
    finished_bid = Decimal('0.00')
    cancelled_count = 0
    cancelled_bid = Decimal('0.00')
    
    # Get user's bids
    user_bids = Comment.query.filter_by(
        commenter_id=current_user.id,
        commenter_type='requester'
    ).filter(Comment.bid_amount > 0).all()
    
    for bid in user_bids:
        total_bid_amount += bid.bid_amount
        fr = FeatureRequest.query.get(bid.feature_request_id)
        if fr:
            if fr.status == 'in_progress':
                in_progress_count += 1
                in_progress_bid += bid.bid_amount
            elif fr.status in ['completed', 'confirmed']:
                finished_count += 1
                finished_bid += bid.bid_amount
            elif fr.status == 'cancelled':
                cancelled_count += 1
                cancelled_bid += bid.bid_amount
    
    # Get requests in approve mode (completed but not confirmed)
    approve_mode_requests = FeatureRequest.query.join(Comment).filter(
        Comment.commenter_id == current_user.id,
        Comment.commenter_type == 'requester',
        Comment.bid_amount > 0,
        FeatureRequest.status == 'completed'
    ).distinct().all()
    
    return {
        'total_requests': total_requests,
        'total_bid_amount': total_bid_amount,
        'in_progress_count': in_progress_count,
        'in_progress_bid': in_progress_bid,
        'finished_count': finished_count,
        'finished_bid': finished_bid,
        'cancelled_count': cancelled_count,
        'cancelled_bid': cancelled_bid,
        'approve_mode_requests': approve_mode_requests,
        'user_requests': user_requests[:10]  # Latest 10
    }

def get_developer_stats():
    """Get statistics for developer user."""
    from app.models import FeatureRequestDeveloper, PaymentRatio
    
    # Get requests being worked on
    dev_requests = FeatureRequest.query.join(FeatureRequestDeveloper).filter(
        FeatureRequestDeveloper.developer_id == current_user.id,
        FeatureRequestDeveloper.removed_at.is_(None)
    ).all()
    
    in_progress_count = len([r for r in dev_requests if r.status == 'in_progress'])
    in_progress_bid = sum([r.total_bid_amount for r in dev_requests if r.status == 'in_progress'])
    
    finished_count = len([r for r in dev_requests if r.status in ['completed', 'confirmed']])
    finished_bid = sum([r.total_bid_amount for r in dev_requests if r.status in ['completed', 'confirmed']])
    
    # Get payments received
    payments_received = PaymentTransaction.query.filter_by(
        user_id=current_user.id,
        direction='paid'
    ).all()
    
    finished_since_last_pay_count = 0
    finished_since_last_pay_bid = Decimal('0.00')
    unpaid_finished_bid = Decimal('0.00')
    
    # TODO: Calculate finished since last pay and unpaid amounts
    # This would require tracking last payment date
    
    # Get approval requests (requests where another dev needs approval)
    approval_requests = []
    for req in dev_requests:
        if req.status == 'in_progress':
            # Check if there are unapproved developers
            unapproved_devs = FeatureRequestDeveloper.query.filter_by(
                feature_request_id=req.id,
                is_approved=False,
                removed_at=None
            ).filter(FeatureRequestDeveloper.developer_id != current_user.id).first()
            if unapproved_devs:
                approval_requests.append(req)
    
    # Get ratio mode requests (requests with multiple devs that need payment ratios set)
    ratio_mode_requests = []
    for req in dev_requests:
        if req.status in ['completed', 'confirmed']:
            active_devs = FeatureRequestDeveloper.query.filter_by(
                feature_request_id=req.id,
                removed_at=None
            ).count()
            if active_devs > 1:
                # Check if all devs have accepted ratios
                ratios = PaymentRatio.query.filter_by(feature_request_id=req.id).all()
                if not ratios or not all(r.is_accepted for r in ratios):
                    ratio_mode_requests.append(req)
    
    return {
        'in_progress_count': in_progress_count,
        'in_progress_bid': in_progress_bid,
        'finished_count': finished_count,
        'finished_bid': finished_bid,
        'finished_since_last_pay_count': finished_since_last_pay_count,
        'finished_since_last_pay_bid': finished_since_last_pay_bid,
        'unpaid_finished_bid': unpaid_finished_bid,
        'dev_requests': dev_requests[:10],  # Latest 10
        'approval_requests': approval_requests,
        'ratio_mode_requests': ratio_mode_requests
    }


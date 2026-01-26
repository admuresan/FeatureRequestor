# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Stripe Connect routes.
See instructions/architecture for development guidelines.
"""

import os
import stripe
from flask import Blueprint, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app import db
from app.models import User
from app.config import get_stripe_key

bp = Blueprint('stripe', __name__, url_prefix='/stripe')

# Initialize Stripe - will be set in each route that needs it
def init_stripe():
    """Initialize Stripe API key from config or environment."""
    stripe.api_key = get_stripe_key('stripe_secret_key')

@bp.route('/connect')
@login_required
def connect():
    """Stripe Connect OAuth flow initiation."""
    # Prevent Stripe operations when in view-as mode
    if session.get('view_as_user_id'):
        flash('Stripe operations are disabled in view-as mode.', 'error')
        return redirect(url_for('account.settings'))
    
    init_stripe()
    if not stripe.api_key:
        flash('Stripe is not configured. Please contact an administrator.', 'error')
        return redirect(url_for('account.settings'))
    
    # Create OAuth link
    client_id = get_stripe_key('stripe_client_id')
    redirect_uri = request.url_root.rstrip('/') + url_for('stripe.callback')
    
    oauth_link = f"https://connect.stripe.com/oauth/authorize?response_type=code&client_id={client_id}&scope=read_write&redirect_uri={redirect_uri}"
    
    return redirect(oauth_link)

@bp.route('/callback')
@login_required
def callback():
    """Stripe Connect OAuth callback."""
    # Prevent Stripe operations when in view-as mode
    if session.get('view_as_user_id'):
        flash('Stripe operations are disabled in view-as mode.', 'error')
        return redirect(url_for('account.settings'))
    
    init_stripe()
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        flash(f'Stripe connection error: {error}', 'error')
        return redirect(url_for('account.settings'))
    
    if not code:
        flash('No authorization code received.', 'error')
        return redirect(url_for('account.settings'))
    
    try:
        # Exchange code for access token
        response = stripe.OAuth.token(
            grant_type='authorization_code',
            code=code
        )
        
        # Get connected account ID
        connected_account_id = response.get('stripe_user_id')
        
        if connected_account_id:
            # Update user's Stripe account info
            current_user.stripe_account_id = connected_account_id
            current_user.stripe_account_status = 'connected'
            db.session.commit()
            
            flash('Stripe account connected successfully!', 'success')
        else:
            flash('Failed to retrieve Stripe account information.', 'error')
    
    except stripe.error.StripeError as e:
        flash(f'Stripe error: {str(e)}', 'error')
    except Exception as e:
        flash(f'Error connecting Stripe account: {str(e)}', 'error')
    
    return redirect(url_for('account.settings'))

@bp.route('/disconnect', methods=['POST'])
@login_required
def disconnect():
    """Disconnect Stripe account."""
    # Prevent Stripe operations when in view-as mode
    if session.get('view_as_user_id'):
        flash('Stripe operations are disabled in view-as mode.', 'error')
        return redirect(url_for('account.settings'))
    
    current_user.stripe_account_id = None
    current_user.stripe_account_status = 'disconnected'
    db.session.commit()
    
    flash('Stripe account disconnected.', 'info')
    return redirect(url_for('account.settings'))


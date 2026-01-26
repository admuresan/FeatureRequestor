# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Apps routes (browse apps, app pages).
See instructions/architecture for development guidelines.
"""

import os
import stripe
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import App, PaymentTransaction, User, FeatureRequest, Comment, FeatureRequestDeveloper
from app.config import get_stripe_key
from decimal import Decimal
from datetime import datetime
from functools import wraps

bp = Blueprint('apps', __name__, url_prefix='/apps')

# Initialize Stripe - will be set in routes that need it
def init_stripe():
    """Initialize Stripe API key from config or environment."""
    stripe.api_key = get_stripe_key('stripe_secret_key')

def calculate_minimum_tip_amount() -> Decimal:
    """
    Calculate the minimum tip amount required to cover Stripe fees.
    Stripe fees: 2.9% + $0.30
    Minimum tip must satisfy: tip - (tip * 0.029 + 0.30) > 0
    Solving: tip > 0.30 / (1 - 0.029) ≈ 0.309
    We round up to $0.50 for practical purposes.
    """
    # Calculate exact minimum: 0.30 / (1 - 0.029) = 0.30 / 0.971 ≈ 0.309
    exact_minimum = Decimal('0.30') / Decimal('0.971')
    # Round up to nearest $0.10 for practical minimum
    return Decimal('0.50')

@bp.route('')
def browse():
    """Browse apps page (public)."""
    apps = App.query.all()
    return render_template('apps/browse.html', apps=apps)

@bp.route('/<app_name>')
def detail(app_name):
    """App detail page (public)."""
    app = App.query.filter_by(app_name=app_name).first_or_404()
    
    # Get tip stats for app owner
    tip_stats = None
    if app.app_owner and app.app_owner.stripe_account_id:
        tips = PaymentTransaction.query.filter_by(
            app_id=app.id,
            transaction_type='tip',
            direction='tip'
        ).all()
        total_tips = sum([t.amount for t in tips])
        tip_stats = {
            'count': len(tips),
            'total': total_tips
        }
    
    return render_template('apps/detail.html', app=app, tip_stats=tip_stats)

@bp.route('/<app_name>/tip', methods=['GET', 'POST'])
def tip_jar(app_name):
    """Tip jar for app."""
    app = App.query.filter_by(app_name=app_name).first_or_404()
    
    if not app.app_owner or not app.app_owner.stripe_account_id:
        flash('This app owner has not set up payment receiving.', 'error')
        return redirect(url_for('apps.detail', app_name=app_name))
    
    if request.method == 'POST':
        amount = request.form.get('amount', type=float)
        email = request.form.get('email', '')
        is_guest = not current_user.is_authenticated
        
        if not amount or amount <= 0:
            flash('Please enter a valid tip amount.', 'error')
            return render_template('apps/tip_jar.html', app=app, minimum_tip=calculate_minimum_tip_amount())
        
        # Validate that tip amount is greater than minimum Stripe fees
        minimum_tip = calculate_minimum_tip_amount()
        if Decimal(str(amount)) < minimum_tip:
            flash(f'Tip amount must be at least ${minimum_tip:.2f} to cover Stripe processing fees.', 'error')
            return render_template('apps/tip_jar.html', app=app, minimum_tip=minimum_tip)
        
        if is_guest:
            # Guest checkout with Stripe Checkout
            init_stripe()
            try:
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'cad',
                            'product_data': {
                                'name': f'Tip for {app.app_display_name}',
                            },
                            'unit_amount': int(amount * 100),  # Convert to cents
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url=request.url_root.rstrip('/') + url_for('apps.tip_success', app_name=app_name),
                    cancel_url=request.url_root.rstrip('/') + url_for('apps.detail', app_name=app_name),
                    customer_email=email if email else None,
                )
                
                # Store tip info in session for after payment
                from flask import session as flask_session
                flask_session['pending_tip'] = {
                    'app_id': app.id,
                    'amount': amount,
                    'email': email,
                    'is_guest': True,
                    'checkout_session_id': checkout_session.id
                }
                
                return redirect(checkout_session.url)
            except Exception as e:
                flash(f'Error creating checkout session: {str(e)}', 'error')
                return render_template('apps/tip_jar.html', app=app, minimum_tip=calculate_minimum_tip_amount())
        else:
            # Authenticated user - direct payment
            if not current_user.stripe_account_id:
                flash('You must connect a Stripe account to tip.', 'error')
                return redirect(url_for('account.settings'))
            
            init_stripe()
            try:
                # Create payment intent
                payment_intent = stripe.PaymentIntent.create(
                    amount=int(amount * 100),
                    currency=current_user.preferred_currency.lower(),
                    transfer_data={
                        'destination': app.app_owner.stripe_account_id,
                    },
                    description=f'Tip for {app.app_display_name}'
                )
                
                # Record transaction
                transaction = PaymentTransaction(
                    user_id=current_user.id,
                    transaction_type='tip',
                    amount=Decimal(str(amount)),
                    currency=current_user.preferred_currency,
                    app_id=app.id,
                    stripe_transaction_id=payment_intent.id,
                    direction='tip',
                    is_guest_transaction=False
                )
                db.session.add(transaction)
                db.session.commit()
                
                flash('Tip processed successfully!', 'success')
                return redirect(url_for('apps.detail', app_name=app_name))
            except Exception as e:
                flash(f'Error processing tip: {str(e)}', 'error')
                return render_template('apps/tip_jar.html', app=app, minimum_tip=calculate_minimum_tip_amount())
    
    return render_template('apps/tip_jar.html', app=app, minimum_tip=calculate_minimum_tip_amount())

@bp.route('/<app_name>/tip/success')
def tip_success(app_name):
    """Tip success page (for guest checkout)."""
    from flask import session as flask_session
    pending_tip = flask_session.get('pending_tip')
    
    if pending_tip and pending_tip.get('app_id'):
        # Record guest transaction
        transaction = PaymentTransaction(
            user_id=None,
            guest_email=pending_tip.get('email'),
            transaction_type='tip',
            amount=Decimal(str(pending_tip.get('amount', 0))),
            currency='CAD',  # Default for guest
            app_id=pending_tip.get('app_id'),
            stripe_transaction_id=pending_tip.get('checkout_session_id'),
            direction='tip',
            is_guest_transaction=True
        )
        db.session.add(transaction)
        db.session.commit()
        
        flask_session.pop('pending_tip', None)
        flash('Thank you for your tip!', 'success')
    
    return redirect(url_for('apps.detail', app_name=app_name))


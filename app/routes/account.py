# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Account management routes.
See instructions/architecture for development guidelines.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from flask_login import login_required, current_user
from app import db
from app.models import User, NotificationPreference, App, PaymentTransaction, RoleChangeRequest
from app.utils.email_verification import create_verification_token, send_verification_email_for_token
from app.utils.pdf_generation import generate_receipt_html, generate_paystub_html, generate_pdf_from_html
from datetime import datetime
from decimal import Decimal
from io import BytesIO
import json

bp = Blueprint('account', __name__, url_prefix='/account')

@bp.route('/settings')
@login_required
def settings():
    """Account settings page."""
    # Get all notification types (excluding new_request which is handled separately)
    notification_types = [
        ('new_message', 'New Message'),
        ('request_status_change', 'My Request Status Change'),
        ('request_comment', 'My Request Comments'),
        ('request_comment_dev', 'Comments on Requests I\'m Working On'),
        ('payment_received', 'Payment Received'),
        ('payment_charged', 'Payment Charged'),
        ('request_approved', 'Request Approved/Denied'),
        ('developer_approval_request', 'Developer Approval Requests'),
        ('group_message_poll_result', 'Group Message Poll Results')
    ]
    
    # Get current preferences
    preferences = {pref.notification_type: pref for pref in NotificationPreference.query.filter_by(user_id=current_user.id).all()}
    
    # Get user's managed apps (apps they own)
    managed_apps = App.query.filter_by(app_owner_id=current_user.id).order_by(App.app_display_name).all()
    
    # Get app-specific notification rules for new_request
    app_rules = []
    new_request_pref = preferences.get('new_request')
    if new_request_pref and new_request_pref.custom_rule:
        try:
            custom_rules = json.loads(new_request_pref.custom_rule)
            app_rules = custom_rules if isinstance(custom_rules, list) else []
        except:
            app_rules = []
    
    # Get pending role change request if user is a requester
    pending_role_change = None
    if current_user.role == 'requester':
        pending_role_change = RoleChangeRequest.query.filter_by(
            user_id=current_user.id,
            status='pending'
        ).first()
    
    return render_template('account/settings.html', 
                         notification_types=notification_types,
                         preferences=preferences,
                         managed_apps=managed_apps,
                         app_rules=app_rules,
                         pending_role_change=pending_role_change)

@bp.route('/update', methods=['POST'])
@login_required
def update():
    """Update account information."""
    name = request.form.get('name')
    email = request.form.get('email')
    preferred_currency = request.form.get('preferred_currency')
    
    if not name or not email:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Name and email are required.'}), 400
        flash('Name and email are required.', 'error')
        return redirect(url_for('account.settings'))
    
    if preferred_currency not in ['CAD', 'USD', 'EUR']:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Invalid currency selected.'}), 400
        flash('Invalid currency selected.', 'error')
        return redirect(url_for('account.settings'))
    
    # Check if email changed
    email_changed = email != current_user.email
    
    current_user.name = name
    current_user.preferred_currency = preferred_currency
    
    if email_changed:
        # Store old email temporarily (don't update email yet)
        old_email = current_user.email
        
        # Create email verification token
        token = create_verification_token(
            email=email,
            verification_type='email_change',
            user_id=current_user.id,
            old_email=old_email
        )
        
        # Send verification email
        base_url = request.url_root.rstrip('/')
        send_verification_email_for_token(token, base_url)
        
        # Set email_verified to False (but keep old email active)
        current_user.email_verified = False
        
        # Store new email in a temporary field or keep old email until verified
        # For now, we'll update the email but mark as unverified
        # The verification process will complete the change
        # Note: In a more robust implementation, you might want to store pending_email
        current_user.email = email  # Update email, but it's unverified
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            db.session.commit()
            return jsonify({
                'success': True,
                'email_changed': True,
                'message': f'Email address changed. Please verify your new email address by clicking the link sent to {email}. Verification links expire after 24 hours.'
            })
        flash(f'Email address changed. Please verify your new email address by clicking the link sent to {email}. Verification links expire after 24 hours.', 'info')
    else:
        current_user.email = email
    
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Account updated successfully!'})
    
    flash('Account updated successfully!', 'success')
    return redirect(url_for('account.settings'))

@bp.route('/resend-verification', methods=['POST'])
@login_required
def resend_verification():
    """Resend email verification email."""
    try:
        if current_user.email_verified:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'Your email is already verified.'}), 400
            flash('Your email is already verified.', 'info')
            return redirect(url_for('account.settings'))
        
        # Create new verification token
        token = create_verification_token(
            email=current_user.email,
            verification_type='signup',
            user_id=current_user.id
        )
        
        # Send verification email
        base_url = request.url_root.rstrip('/')
        email_sent = send_verification_email_for_token(token, base_url)
        
        if email_sent:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': 'Verification email sent! Please check your inbox (including spam folder).'})
            flash('Verification email sent! Please check your inbox (including spam folder).', 'success')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'Verification email could not be sent. Please check your email configuration or try again later.'}), 500
            flash('Verification email could not be sent. Please check your email configuration or try again later.', 'error')
        
        return redirect(url_for('account.settings'))
    except Exception as e:
        error_msg = f'An error occurred while sending the verification email: {str(e)}'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': error_msg}), 500
        flash(error_msg, 'error')
        return redirect(url_for('account.settings'))

@bp.route('/request-password-reset', methods=['GET', 'POST'])
def request_password_reset():
    """Request password reset (public route)."""
    # Prevent password reset when in view-as mode
    if session.get('view_as_user_id'):
        flash('Password changes are disabled in view-as mode.', 'error')
        return redirect(url_for('account.settings'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('Email address is required.', 'error')
            return render_template('account/request_password_reset.html')
        
        # Try to find user by email (for password reset, we still use email)
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Create password reset token
            from app.utils.email_verification import create_verification_token
            token = create_verification_token(
                email=email,
                verification_type='password_reset',
                user_id=user.id
            )
            
            # Send password reset email
            from app.utils.email import send_email
            from app.config import get_config_value
            import json
            from pathlib import Path
            
            # Load email templates
            instance_path = Path(__file__).parent.parent.parent / 'instance'
            templates_file = instance_path / 'email_templates.json'
            if templates_file.exists():
                with open(templates_file, 'r') as f:
                    templates = json.load(f)
            else:
                templates = {}
            
            reset_template = templates.get('password_reset', {})
            subject = reset_template.get('subject', 'Password Reset Request')
            body_template = reset_template.get('body', '<p>Click <a href="{reset_link}">here</a> to reset your password.</p>')
            
            base_url = request.url_root.rstrip('/')
            reset_link = f"{base_url}/account/reset-password?token={token.token}"
            
            body = body_template.format(
                user_name=user.name,
                reset_link=reset_link
            )
            
            send_email(user.email, subject, body)
        
        # Always show success message (security: don't reveal if email exists)
        flash('If an account with that email exists, a password reset link has been sent.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('account/request_password_reset.html')

@bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Reset password using token."""
    token_string = request.args.get('token') or request.form.get('token')
    
    if not token_string:
        flash('Invalid reset link.', 'error')
        return redirect(url_for('auth.login'))
    
    from app.utils.email_verification import verify_token
    # Don't verify yet - we need to check the token first
    from app.models import EmailVerificationToken
    token = EmailVerificationToken.query.filter_by(token=token_string).first()
    
    if not token:
        flash('Invalid reset link.', 'error')
        return redirect(url_for('auth.login'))
    
    if token.is_expired():
        flash('Reset link has expired. Please request a new one.', 'error')
        return redirect(url_for('account.request_password_reset'))
    
    if token.verified_at:
        flash('This reset link has already been used. Please request a new one.', 'error')
        return redirect(url_for('account.request_password_reset'))
    
    if token.verification_type != 'password_reset':
        flash('Invalid reset link.', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not new_password or not confirm_password:
            flash('Please fill in all fields.', 'error')
            return render_template('account/reset_password.html', token=token_string)
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('account/reset_password.html', token=token_string)
        
        if len(new_password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('account/reset_password.html', token=token_string)
        
        # Update password
        from app.utils.auth import hash_password
        user = User.query.get(token.user_id)
        if user:
            user.password_hash = hash_password(new_password)
            # Mark token as verified so it can't be reused
            token.verified_at = datetime.utcnow()
            db.session.commit()
            flash('Password reset successfully! You can now log in with your new password.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('User not found.', 'error')
            return redirect(url_for('auth.login'))
    
    return render_template('account/reset_password.html', token=token_string)

@bp.route('/notification-preferences', methods=['GET', 'POST'])
@login_required
def notification_preferences():
    """Notification preferences management page."""
    if request.method == 'POST':
        # Handle preference updates
        notification_type = request.form.get('notification_type')
        preference = request.form.get('preference')
        custom_rule = request.form.get('custom_rule', '')
        
        if notification_type and preference in ['none', 'immediate', 'bulk']:
            # Find or create preference
            pref = NotificationPreference.query.filter_by(
                user_id=current_user.id,
                notification_type=notification_type
            ).first()
            
            if pref:
                pref.preference = preference
                if custom_rule:
                    pref.custom_rule = custom_rule
                pref.updated_at = datetime.utcnow()
            else:
                pref = NotificationPreference(
                    user_id=current_user.id,
                    notification_type=notification_type,
                    preference=preference,
                    custom_rule=custom_rule if custom_rule else None
                )
                db.session.add(pref)
            
            db.session.commit()
            
            # Support AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': 'Notification preference updated!'})
            
            flash('Notification preference updated!', 'success')
            return redirect(url_for('account.notification_preferences'))
    
    # Get all notification types
    notification_types = [
        ('new_message', 'New Message'),
        ('new_request', 'New Request by App'),
        ('request_status_change', 'My Request Status Change'),
        ('request_comment', 'My Request Comments'),
        ('request_comment_dev', 'Comments on Requests I\'m Working On'),
        ('payment_received', 'Payment Received'),
        ('payment_charged', 'Payment Charged'),
        ('request_approved', 'Request Approved/Denied'),
        ('developer_approval_request', 'Developer Approval Requests'),
        ('group_message_poll_result', 'Group Message Poll Results')
    ]
    
    # Get current preferences
    preferences = {pref.notification_type: pref for pref in NotificationPreference.query.filter_by(user_id=current_user.id).all()}
    
    # Get all apps for custom rules
    all_apps = App.query.all()
    
    # Parse custom rules for display
    parsed_preferences = {}
    for notif_type, pref in preferences.items():
        parsed_preferences[notif_type] = {
            'preference': pref.preference,
            'custom_rule': json.loads(pref.custom_rule) if pref.custom_rule else None
        }
    
    return render_template('account/notification_preferences.html',
                         notification_types=notification_types,
                         preferences=preferences,
                         parsed_preferences=parsed_preferences,
                         all_apps=all_apps)

@bp.route('/notification-preferences/add-rule', methods=['POST'])
@login_required
def add_notification_rule():
    """Add a custom notification rule for 'new_request by app'."""
    app_id = request.form.get('app_id', type=int)
    preference = request.form.get('preference')
    
    if not app_id or preference not in ['none', 'immediate', 'bulk']:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Invalid rule data.'}), 400
        flash('Invalid rule data.', 'error')
        return redirect(url_for('account.settings'))
    
    app = App.query.get(app_id)
    if not app:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'App not found.'}), 404
        flash('App not found.', 'error')
        return redirect(url_for('account.settings'))
    
    # Verify user owns this app
    if app.app_owner_id != current_user.id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'You do not own this app.'}), 403
        flash('You do not own this app.', 'error')
        return redirect(url_for('account.settings'))
    
    # Get existing preference or create new
    pref = NotificationPreference.query.filter_by(
        user_id=current_user.id,
        notification_type='new_request'
    ).first()
    
    # Parse existing custom rules
    custom_rules = []
    if pref and pref.custom_rule:
        try:
            custom_rules = json.loads(pref.custom_rule)
        except:
            custom_rules = []
    
    # Add or update rule for this app
    rule_exists = False
    for rule in custom_rules:
        if rule.get('app_id') == app_id:
            rule['preference'] = preference
            rule['app_name'] = app.app_display_name  # Update name in case it changed
            rule_exists = True
            break
    
    if not rule_exists:
        custom_rules.append({
            'app_id': app_id,
            'app_name': app.app_display_name,
            'preference': preference
        })
    
    # Update preference
    if pref:
        pref.custom_rule = json.dumps(custom_rules)
        pref.updated_at = datetime.utcnow()
    else:
        pref = NotificationPreference(
            user_id=current_user.id,
            notification_type='new_request',
            preference='none',  # Default to none since we're using app-specific rules
            custom_rule=json.dumps(custom_rules)
        )
        db.session.add(pref)
    
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True, 
            'message': f'Notification rule added for {app.app_display_name}!',
            'rule': {
                'app_id': app_id,
                'app_name': app.app_display_name,
                'preference': preference
            }
        })
    
    flash(f'Notification rule added for {app.app_display_name}!', 'success')
    return redirect(url_for('account.settings'))

@bp.route('/notification-preferences/remove-rule', methods=['POST'])
@login_required
def remove_notification_rule():
    """Remove a custom notification rule."""
    app_id = request.form.get('app_id', type=int)
    
    if not app_id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Invalid app ID.'}), 400
        flash('Invalid app ID.', 'error')
        return redirect(url_for('account.settings'))
    
    pref = NotificationPreference.query.filter_by(
        user_id=current_user.id,
        notification_type='new_request'
    ).first()
    
    if pref and pref.custom_rule:
        try:
            custom_rules = json.loads(pref.custom_rule)
            custom_rules = [r for r in custom_rules if r.get('app_id') != app_id]
            pref.custom_rule = json.dumps(custom_rules) if custom_rules else None
            pref.updated_at = datetime.utcnow()
            db.session.commit()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': 'Notification rule removed!'})
            
            flash('Notification rule removed!', 'success')
        except:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'Error removing rule.'}), 500
            flash('Error removing rule.', 'error')
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Rule not found.'}), 404
    
    return redirect(url_for('account.settings'))

@bp.route('/payment-history')
@login_required
def payment_history():
    """View payment transaction history."""
    # For requesters: show payments they made (charged/tip)
    # For devs: show two sections - received (paid) and paid (charged/tip)
    
    if current_user.role == 'requester':
        # Requesters see payments they made
        transactions = PaymentTransaction.query.filter(
            PaymentTransaction.user_id == current_user.id,
            PaymentTransaction.direction.in_(['charged', 'tip'])
        ).order_by(PaymentTransaction.transaction_date.desc()).all()
        
        # Calculate totals by currency
        totals_by_currency = {}
        for transaction in transactions:
            currency = transaction.currency
            if currency not in totals_by_currency:
                totals_by_currency[currency] = Decimal('0.00')
            totals_by_currency[currency] += transaction.amount
        
        return render_template('account/payment_history.html',
                             transactions=transactions,
                             totals_by_currency=totals_by_currency,
                             received_transactions=None,
                             paid_transactions=None,
                             received_totals=None,
                             paid_totals=None)
    else:
        # Devs see two sections: received (paid) and paid (charged/tip)
        received_transactions = PaymentTransaction.query.filter(
            PaymentTransaction.user_id == current_user.id,
            PaymentTransaction.direction == 'paid'
        ).order_by(PaymentTransaction.transaction_date.desc()).all()
        
        paid_transactions = PaymentTransaction.query.filter(
            PaymentTransaction.user_id == current_user.id,
            PaymentTransaction.direction.in_(['charged', 'tip'])
        ).order_by(PaymentTransaction.transaction_date.desc()).all()
        
        # Calculate totals for received payments
        received_totals = {}
        for transaction in received_transactions:
            currency = transaction.currency
            if currency not in received_totals:
                received_totals[currency] = Decimal('0.00')
            received_totals[currency] += transaction.amount
        
        # Calculate totals for paid payments
        paid_totals = {}
        for transaction in paid_transactions:
            currency = transaction.currency
            if currency not in paid_totals:
                paid_totals[currency] = Decimal('0.00')
            paid_totals[currency] += transaction.amount
        
        return render_template('account/payment_history.html',
                             transactions=None,
                             totals_by_currency=None,
                             received_transactions=received_transactions,
                             paid_transactions=paid_transactions,
                             received_totals=received_totals,
                             paid_totals=paid_totals)

@bp.route('/generate-receipt-pdf', methods=['POST'])
@login_required
def generate_receipt_pdf():
    """Generate receipt PDF for payments made."""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    
    if not start_date_str or not end_date_str:
        if is_ajax:
            return jsonify({'error': 'Please select both start and end dates.'}), 400
        flash('Please select both start and end dates.', 'error')
        return redirect(url_for('account.payment_history'))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        # Set end_date to end of day (23:59:59)
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    except ValueError:
        if is_ajax:
            return jsonify({'error': 'Invalid date format.'}), 400
        flash('Invalid date format.', 'error')
        return redirect(url_for('account.payment_history'))
    
    # Get transactions for payments made (charged/tip)
    transactions = PaymentTransaction.query.filter(
        PaymentTransaction.user_id == current_user.id,
        PaymentTransaction.direction.in_(['charged', 'tip']),
        PaymentTransaction.transaction_date >= start_date,
        PaymentTransaction.transaction_date <= end_date
    ).all()
    
    if not transactions:
        if is_ajax:
            return jsonify({'error': 'No transactions found for the selected date range.'}), 404
        flash('No transactions found for the selected date range.', 'info')
        return redirect(url_for('account.payment_history'))
    
    try:
        # Generate PDF
        html = generate_receipt_html(current_user, transactions, start_date, end_date)
        pdf_bytes = generate_pdf_from_html(html)
        
        # Return PDF
        return send_file(
            BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'receipt_{start_date_str}_to_{end_date_str}.pdf'
        )
    except Exception as e:
        if is_ajax:
            return jsonify({'error': f'Error generating receipt: {str(e)}'}), 500
        flash(f'Error generating receipt: {str(e)}', 'error')
        return redirect(url_for('account.payment_history'))

@bp.route('/generate-paystub-pdf', methods=['POST'])
@login_required
def generate_paystub_pdf():
    """Generate paystub PDF for received payments (devs only)."""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if current_user.role != 'dev':
        if is_ajax:
            return jsonify({'error': 'Paystubs are only available for developers.'}), 403
        flash('Paystubs are only available for developers.', 'error')
        return redirect(url_for('account.payment_history'))
    
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    
    if not start_date_str or not end_date_str:
        if is_ajax:
            return jsonify({'error': 'Please select both start and end dates.'}), 400
        flash('Please select both start and end dates.', 'error')
        return redirect(url_for('account.payment_history'))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        # Set end_date to end of day (23:59:59)
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    except ValueError:
        if is_ajax:
            return jsonify({'error': 'Invalid date format.'}), 400
        flash('Invalid date format.', 'error')
        return redirect(url_for('account.payment_history'))
    
    # Get transactions for received payments (paid)
    transactions = PaymentTransaction.query.filter(
        PaymentTransaction.user_id == current_user.id,
        PaymentTransaction.direction == 'paid',
        PaymentTransaction.transaction_date >= start_date,
        PaymentTransaction.transaction_date <= end_date
    ).all()
    
    if not transactions:
        if is_ajax:
            return jsonify({'error': 'No payments found for the selected date range.'}), 404
        flash('No payments found for the selected date range.', 'info')
        return redirect(url_for('account.payment_history'))
    
    try:
        # Generate PDF
        html = generate_paystub_html(current_user, transactions, start_date, end_date)
        pdf_bytes = generate_pdf_from_html(html)
        
        # Return PDF
        return send_file(
            BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'paystub_{start_date_str}_to_{end_date_str}.pdf'
        )
    except Exception as e:
        if is_ajax:
            return jsonify({'error': f'Error generating paystub: {str(e)}'}), 500
        flash(f'Error generating paystub: {str(e)}', 'error')
        return redirect(url_for('account.payment_history'))

@bp.route('/request-role-upgrade', methods=['POST'])
@login_required
def request_role_upgrade():
    """Request to upgrade from requester to dev role."""
    # Only requesters can request role upgrade
    if current_user.role != 'requester':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Only requester accounts can request role upgrade.'}), 403
        flash('Only requester accounts can request role upgrade.', 'error')
        return redirect(url_for('account.settings'))
    
    # Check if there's already a pending request
    existing_request = RoleChangeRequest.query.filter_by(
        user_id=current_user.id,
        status='pending'
    ).first()
    
    if existing_request:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'You already have a pending role upgrade request.'}), 400
        flash('You already have a pending role upgrade request.', 'info')
        return redirect(url_for('account.settings'))
    
    # Create new role change request
    role_change_request = RoleChangeRequest(
        user_id=current_user.id,
        requested_role='dev',
        status='pending'
    )
    db.session.add(role_change_request)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': 'Role upgrade request submitted! An admin will review your request. You will continue with your requester account until approved.'
        })
    
    flash('Role upgrade request submitted! An admin will review your request. You will continue with your requester account until approved.', 'success')
    return redirect(url_for('account.settings'))


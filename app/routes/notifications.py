# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Notifications routes.
See instructions/architecture for development guidelines.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Notification
from app.utils.notifications import get_user_notifications, mark_notification_read

bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@bp.route('')
@login_required
def index():
    """Notifications page."""
    # Get all notifications for the user (not just unread, no limit)
    # Exclude message notifications since those are handled in the messages page
    all_notifications = get_user_notifications(current_user.id, unread_only=False, limit=None)
    notifications = [n for n in all_notifications if n.notification_type not in ['new_message', 'message_received']]
    
    # Count unread notifications (excluding message notifications)
    unread_count = len([n for n in notifications if not n.is_read])
    
    return render_template('notifications/index.html', 
                         notifications=notifications,
                         unread_count=unread_count)

@bp.route('/<int:notification_id>/mark-read', methods=['POST'])
@login_required
def mark_read(notification_id):
    """Mark a notification as read."""
    mark_notification_read(notification_id, current_user.id)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    
    flash('Notification marked as read.', 'success')
    return redirect(url_for('notifications.index'))

@bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    """Mark all notifications as read (excluding message notifications)."""
    notifications = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).filter(
        Notification.notification_type != 'new_message',
        Notification.notification_type != 'message_received'
    ).all()
    
    for notification in notifications:
        notification.is_read = True
        from datetime import datetime
        notification.read_at = datetime.utcnow()
    
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'count': len(notifications)})
    
    flash(f'Marked {len(notifications)} notifications as read.', 'success')
    return redirect(url_for('notifications.index'))


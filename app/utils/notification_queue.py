# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Notification queue manager for bulk email notifications.
Implements 30-minute timer system for queuing notifications.
See instructions/architecture for development guidelines.
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, List
from app import db
from app.models import Notification, User
from app.utils.email import send_email
from app.config import load_email_templates

# In-memory queue: {user_id: {'notifications': [notification_ids], 'timer_expires_at': datetime}}
_notification_queue: Dict[int, Dict] = {}
_queue_lock = Lock()

# Timer duration: 30 minutes
TIMER_DURATION = timedelta(minutes=30)

def add_to_queue(user_id: int, notification_id: int, reset_timer: bool = True):
    """
    Add a notification to the user's queue.
    If reset_timer is True, reset the 30-minute timer.
    
    Args:
        user_id: User ID
        notification_id: Notification ID to queue
        reset_timer: If True, reset the timer (default: True)
    """
    with _queue_lock:
        if user_id not in _notification_queue:
            _notification_queue[user_id] = {
                'notifications': [],
                'timer_expires_at': None
            }
        
        # Add notification if not already in queue
        if notification_id not in _notification_queue[user_id]['notifications']:
            _notification_queue[user_id]['notifications'].append(notification_id)
        
        # Reset timer if requested
        if reset_timer:
            _notification_queue[user_id]['timer_expires_at'] = datetime.utcnow() + TIMER_DURATION

def get_queued_notifications(user_id: int) -> List[int]:
    """
    Get list of notification IDs in queue for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        List of notification IDs
    """
    with _queue_lock:
        if user_id not in _notification_queue:
            return []
        return _notification_queue[user_id]['notifications'].copy()

def get_timer_expiry(user_id: int) -> datetime:
    """
    Get when the timer expires for a user's queue.
    
    Args:
        user_id: User ID
    
    Returns:
        datetime when timer expires, or None if no timer set
    """
    with _queue_lock:
        if user_id not in _notification_queue:
            return None
        return _notification_queue[user_id]['timer_expires_at']

def clear_queue(user_id: int):
    """
    Clear the notification queue for a user.
    
    Args:
        user_id: User ID
    """
    with _queue_lock:
        if user_id in _notification_queue:
            del _notification_queue[user_id]

def send_bulk_notification_email(user_id: int) -> bool:
    """
    Send a bulk email with all queued notifications for a user.
    Clears the queue after sending.
    
    Args:
        user_id: User ID
    
    Returns:
        True if email sent successfully, False otherwise
    """
    # Get queued notifications
    notification_ids = get_queued_notifications(user_id)
    
    if not notification_ids:
        return False
    
    # Get user
    user = User.query.get(user_id)
    if not user or not user.email:
        clear_queue(user_id)
        return False
    
    # Get notifications from database
    notifications = Notification.query.filter(
        Notification.id.in_(notification_ids),
        Notification.user_id == user_id
    ).order_by(Notification.created_at.asc()).all()
    
    if not notifications:
        clear_queue(user_id)
        return False
    
    # Build email content
    subject = f"Feature Requestor: {len(notifications)} Notification(s)"
    
    # Build HTML body
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .notification {{ margin-bottom: 20px; padding: 15px; border-left: 4px solid #007bff; background-color: #f8f9fa; }}
            .notification-type {{ font-weight: bold; color: #007bff; margin-bottom: 5px; }}
            .notification-message {{ margin-bottom: 10px; }}
            .notification-link {{ margin-top: 10px; }}
            .notification-link a {{ background-color: #007bff; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <h2>You have {len(notifications)} new notification(s)</h2>
    """
    
    # Add each notification with improved context
    for notification in notifications:
        # Get rendered message and link
        rendered_message = notification.get_rendered_message()
        rendered_link = notification.get_rendered_link()
        
        link_html = ""
        if rendered_link:
            # Determine link text based on notification type
            link_text = "View Request"
            if 'message' in notification.notification_type:
                link_text = "View Messages"
            elif 'payment' in notification.notification_type:
                link_text = "View Payment History"
            elif 'developer' in notification.notification_type or 'request' in notification.notification_type:
                link_text = "View Request"
            else:
                link_text = "View Details"
            
            # Convert relative URL to absolute URL for email
            email_link = rendered_link
            if not rendered_link.startswith(('http://', 'https://')):
                from flask import request
                try:
                    base_url = request.url_root.rstrip('/')
                    email_link = f"{base_url}{rendered_link}"
                except RuntimeError:
                    email_link = rendered_link
            
            link_html = f'<div class="notification-link"><a href="{email_link}">{link_text}</a></div>'
        
        html_body += f"""
        <div class="notification">
            <div class="notification-type">{notification.notification_type.replace('_', ' ').title()}</div>
            <div class="notification-message">{rendered_message}</div>
            <div style="color: #666; font-size: 12px; margin-top: 10px;">{notification.created_at.strftime('%Y-%m-%d %H:%M')}</div>
            {link_html}
        </div>
        """
    
    html_body += """
        <div class="footer">
            <p>This is a bulk notification email from Feature Requestor.</p>
            <p>You can change your notification preferences in your account settings.</p>
        </div>
    </body>
    </html>
    """
    
    # Build plain text body
    text_body = f"You have {len(notifications)} new notification(s):\n\n"
    for notification in notifications:
        rendered_message = notification.get_rendered_message()
        rendered_link = notification.get_rendered_link()
        
        text_body += f"{notification.notification_type.replace('_', ' ').title()}\n"
        text_body += f"{rendered_message}\n"
        text_body += f"Date: {notification.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        if rendered_link:
            text_body += f"Link: {rendered_link}\n"
        text_body += "\n"
    
    text_body += "\nYou can change your notification preferences in your account settings."
    
    # Send email
    success = send_email(user.email, subject, html_body, text_body)
    
    # Clear queue after sending (regardless of success)
    clear_queue(user_id)
    
    return success

def check_and_send_expired_queues():
    """
    Check all queues and send emails for any that have expired timers.
    This should be called periodically (e.g., every minute).
    """
    current_time = datetime.utcnow()
    users_to_process = []
    
    # Find users with expired timers
    with _queue_lock:
        for user_id, queue_data in list(_notification_queue.items()):
            if queue_data['timer_expires_at'] and queue_data['timer_expires_at'] <= current_time:
                users_to_process.append(user_id)
    
    # Send emails for expired queues
    for user_id in users_to_process:
        send_bulk_notification_email(user_id)


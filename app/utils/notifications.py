# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Notification utilities.
See instructions/architecture for development guidelines.
"""

from app import db
from app.models import Notification, NotificationPreference, User
from app.utils.notification_queue import add_to_queue, send_bulk_notification_email
from app.utils.email import send_email
from datetime import datetime

def create_notification(user_id: int, notification_type: str, data: dict):
    """
    Create a notification for a user.
    Respects user's notification preferences:
    - 'none': No email sent, notification only stored
    - 'immediate': Email sent immediately
    - 'bulk': Notification queued for bulk email (30-minute timer)
    
    Args:
        user_id: User ID to notify
        notification_type: Type of notification
        data: Dict with notification data for dynamic rendering (required)
    
    Returns:
        Created Notification object
    """
    if not data:
        raise ValueError("data parameter is required. All notifications must use data-based rendering.")
    
    # Create notification in database
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        notification_message=''  # Empty string for backward compatibility with NOT NULL constraint
    )
    notification.set_data(data)
    
    db.session.add(notification)
    db.session.commit()
    
    # Get user's preference for this notification type
    preference = get_notification_preference(user_id, notification_type)
    
    # Handle based on preference
    if preference == 'none':
        # No email sent, just store notification
        pass
    elif preference == 'immediate':
        # Send email immediately
        send_immediate_notification_email(user_id, notification)
    elif preference == 'bulk':
        # Add to queue with timer reset
        add_to_queue(user_id, notification.id, reset_timer=True)
    
    return notification

def send_immediate_notification_email(user_id: int, notification: Notification):
    """
    Send an immediate email notification.
    
    Args:
        user_id: User ID
        notification: Notification object
    """
    user = User.query.get(user_id)
    if not user or not user.email:
        return
    
    # Build email with improved context
    notification_type_display = notification.notification_type.replace('_', ' ').title()
    subject = f"Feature Requestor: {notification_type_display}"
    
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
    
    # Get rendered message and link
    rendered_message = notification.get_rendered_message()
    rendered_link = notification.get_rendered_link()
    
    # Convert relative URL to absolute URL for email
    email_link = rendered_link
    if rendered_link and not rendered_link.startswith(('http://', 'https://')):
        from flask import request
        # Get base URL from request context or use a default
        try:
            base_url = request.url_root.rstrip('/')
            email_link = f"{base_url}{rendered_link}"
        except RuntimeError:
            # If outside request context, use relative link
            email_link = rendered_link
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .notification {{ padding: 20px; border-left: 4px solid #007bff; background-color: #f8f9fa; margin: 20px 0; }}
            .notification-type {{ font-weight: bold; color: #007bff; margin-bottom: 15px; font-size: 18px; }}
            .notification-message {{ margin-bottom: 20px; font-size: 14px; line-height: 1.8; }}
            .notification-link {{ margin-top: 20px; }}
            .notification-link a {{ background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: 500; }}
            .notification-link a:hover {{ background-color: #0056b3; }}
            .footer {{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="notification">
            <div class="notification-type">{notification_type_display}</div>
            <div class="notification-message">{rendered_message}</div>
    """
    
    if email_link:
        html_body += f'<div class="notification-link"><a href="{email_link}">{link_text}</a></div>'
    
    html_body += """
        </div>
        <div class="footer">
            <p>This is an immediate notification from Feature Requestor.</p>
            <p>You can change your notification preferences in your account settings.</p>
        </div>
    </body>
    </html>
    """
    
    text_body = f"{notification_type_display}\n\n"
    text_body += f"{rendered_message}\n\n"
    if email_link:
        text_body += f"{link_text}: {email_link}\n"
    text_body += "\nYou can change your notification preferences in your account settings."
    
    # Send email
    send_email(user.email, subject, html_body, text_body)

def get_user_notifications(user_id: int, unread_only: bool = False, limit: int = None):
    """
    Get notifications for a user.
    
    Args:
        user_id: User ID
        unread_only: If True, only return unread notifications
        limit: Maximum number of notifications to return
    
    Returns:
        List of Notification objects
    """
    query = Notification.query.filter_by(user_id=user_id)
    
    if unread_only:
        query = query.filter_by(is_read=False)
    
    query = query.order_by(Notification.created_at.desc())
    
    if limit:
        query = query.limit(limit)
    
    return query.all()

def mark_notification_read(notification_id: int, user_id: int):
    """
    Mark a notification as read.
    
    Args:
        notification_id: Notification ID
        user_id: User ID (for security)
    """
    notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if notification and not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.session.commit()

def get_notification_preference(user_id: int, notification_type: str) -> str:
    """
    Get user's notification preference for a type.
    
    Args:
        user_id: User ID
        notification_type: Notification type
    
    Returns:
        Preference: 'none', 'immediate', or 'bulk'
    """
    pref = NotificationPreference.query.filter_by(
        user_id=user_id,
        notification_type=notification_type
    ).first()
    
    return pref.preference if pref else 'immediate'  # Default to immediate


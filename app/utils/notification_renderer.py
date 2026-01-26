# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Notification rendering utilities.
Renders notification messages from stored data using templates.
See instructions/architecture for development guidelines.
"""

from flask import url_for
from app.models import FeatureRequest, User, App, Comment

def render_notification_message(notification):
    """
    Render notification message from stored data.
    
    Args:
        notification: Notification object with notification_data
        
    Returns:
        Rendered message string
    """
    data = notification.get_data()
    if not data:
        raise ValueError(f"Notification {notification.id} has no notification_data. All notifications must use data-based rendering.")
    
    notification_type = notification.notification_type
    
    # Render based on notification type
    if notification_type == 'developer_removed':
        return _render_developer_removed(data)
    elif notification_type == 'developer_added':
        return _render_developer_added(data)
    elif notification_type == 'request_completed':
        return _render_request_completed(data)
    elif notification_type == 'request_status_change':
        return _render_request_status_change(data)
    elif notification_type in ['request_comment', 'request_comment_dev']:
        return _render_request_comment(data, notification_type)
    elif notification_type == 'new_request':
        return _render_new_request(data)
    elif notification_type == 'payment_received':
        return _render_payment_received(data)
    elif notification_type in ['new_message', 'message_received']:
        return _render_message_received(data)
    else:
        # Unknown notification type
        raise ValueError(f"Unknown notification type: {notification_type}")

def render_notification_link(notification):
    """
    Render notification link from stored data.
    
    Args:
        notification: Notification object with notification_data
        
    Returns:
        Rendered link string or None
    """
    data = notification.get_data()
    if not data:
        raise ValueError(f"Notification {notification.id} has no notification_data. All notifications must use data-based rendering.")
    
    notification_type = notification.notification_type
    
    # Generate link based on notification type
    if notification_type in ['developer_removed', 'developer_added', 'request_completed', 
                            'request_status_change', 'request_comment', 'request_comment_dev', 
                            'new_request']:
        request_id = data.get('feature_request_id')
        if request_id:
            return url_for('feature_requests.detail', request_id=request_id)
    elif notification_type == 'payment_received':
        return url_for('account.payment_history')
    elif notification_type in ['new_message', 'message_received']:
        thread_id = data.get('thread_id')
        if thread_id:
            return url_for('messages.index', thread_id=thread_id)
        return url_for('messages.index')
    
    # No link for this notification type
    return None

def _render_developer_removed(data):
    """Render developer removed notification."""
    feature_request = FeatureRequest.query.get(data.get('feature_request_id'))
    if not feature_request:
        return "You have been removed from a feature request."
    
    app_name = feature_request.app.app_display_name if feature_request.app else 'Unknown App'
    message = f"You have been removed from feature request '{feature_request.title}' for {app_name}"
    
    reason = data.get('reason')
    if reason:
        message += f". Reason: {reason}"
    
    request_id = data.get('feature_request_id')
    if request_id:
        message += f". Request ID: #{request_id}"
    
    return message

def _render_developer_added(data):
    """Render developer added notification."""
    feature_request = FeatureRequest.query.get(data.get('feature_request_id'))
    if not feature_request:
        return "You have been added as a developer to a feature request."
    
    app_name = feature_request.app.app_display_name if feature_request.app else 'Unknown App'
    
    # Check if this is for the developer or for requesters
    developer_id = data.get('developer_id')
    developer_name = data.get('developer_name')
    
    if developer_id and developer_name:
        # This is for requesters - someone else was added
        return f"Developer {developer_name} has been added to feature request '{feature_request.title}' for {app_name}"
    else:
        # This is for the developer themselves
        return f"You have been added as a developer to feature request '{feature_request.title}' for {app_name}"

def _render_request_completed(data):
    """Render request completed notification."""
    feature_request = FeatureRequest.query.get(data.get('feature_request_id'))
    if not feature_request:
        return "A feature request has been marked as completed."
    
    app_name = feature_request.app.app_display_name if feature_request.app else 'Unknown App'
    
    # Check if this is for requesters or developers
    completed_by_name = data.get('completed_by_name')
    
    if completed_by_name:
        # This is for other developers
        return f"Feature request '{feature_request.title}' for {app_name} has been marked as completed by {completed_by_name}."
    else:
        # This is for requesters
        return f"Feature request '{feature_request.title}' for {app_name} has been marked as completed. Please review and confirm if the work meets your requirements."

def _render_request_status_change(data):
    """Render request status change notification."""
    feature_request = FeatureRequest.query.get(data.get('feature_request_id'))
    if not feature_request:
        return "A feature request status has been changed."
    
    app_name = feature_request.app.app_display_name if feature_request.app else 'Unknown App'
    old_status = data.get('old_status', '').replace('_', ' ').title()
    new_status = data.get('new_status', '').replace('_', ' ').title()
    changed_by_name = data.get('changed_by_name')
    
    if changed_by_name:
        return f"Feature request '{feature_request.title}' for {app_name} status has been changed from {old_status} to {new_status} by {changed_by_name}."
    else:
        return f"Feature request '{feature_request.title}' for {app_name} status has been changed from {old_status} to {new_status}."

def _render_request_comment(data, notification_type):
    """Render request comment notification."""
    feature_request = FeatureRequest.query.get(data.get('feature_request_id'))
    if not feature_request:
        return "New comment on a feature request."
    
    app_name = feature_request.app.app_display_name if feature_request.app else 'Unknown App'
    comment_preview = data.get('comment_preview', '')
    
    if notification_type == 'request_comment':
        return f"New comment from requester on feature request '{feature_request.title}' for {app_name}: {comment_preview}"
    else:
        return f"New comment from developer on feature request '{feature_request.title}' for {app_name}: {comment_preview}"

def _render_new_request(data):
    """Render new request notification."""
    feature_request = FeatureRequest.query.get(data.get('feature_request_id'))
    if not feature_request:
        return "New feature request created."
    
    app_name = feature_request.app.app_display_name if feature_request.app else 'Unknown App'
    return f"New feature request '{feature_request.title}' for {app_name}"

def _render_payment_received(data):
    """Render payment received notification."""
    amount = data.get('amount')
    currency = data.get('currency', '$')
    
    if amount:
        return f"Payment of {currency}{amount} received"
    return "Payment received"

def _render_message_received(data):
    """Render message received notification."""
    sender_name = data.get('sender_name')
    if sender_name:
        return f"You have a new message from {sender_name}"
    return "You have a new message"


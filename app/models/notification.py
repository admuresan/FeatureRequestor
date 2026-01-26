# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Notification models for user notifications.
See instructions/architecture for development guidelines.
"""

from app import db
from datetime import datetime
import json

class Notification(db.Model):
    """User notification model."""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notification_type = db.Column(db.Text, nullable=False)  # Various types
    notification_message = db.Column(db.Text, nullable=True)  # Deprecated: kept for backward compatibility
    notification_data = db.Column(db.Text, nullable=True)  # JSON data for dynamic rendering
    link = db.Column(db.Text, nullable=True)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='notifications')
    
    def get_data(self):
        """Get notification data as dict."""
        if self.notification_data:
            try:
                return json.loads(self.notification_data)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_data(self, data):
        """Set notification data from dict."""
        self.notification_data = json.dumps(data) if data else None
    
    def render_message(self):
        """Render notification message from data using templates."""
        from app.utils.notification_renderer import render_notification_message
        return render_notification_message(self)
    
    def get_rendered_message(self):
        """Get rendered message from data."""
        if not self.notification_data:
            raise ValueError(f"Notification {self.id} has no notification_data. All notifications must use data-based rendering.")
        return self.render_message()
    
    def get_rendered_link(self):
        """Get rendered link from data."""
        from app.utils.notification_renderer import render_notification_link
        if not self.notification_data:
            raise ValueError(f"Notification {self.id} has no notification_data. All notifications must use data-based rendering.")
        return render_notification_link(self)
    
    def __repr__(self):
        return f'<Notification {self.id}>'

class NotificationPreference(db.Model):
    """User notification preferences."""
    __tablename__ = 'notification_preferences'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notification_type = db.Column(db.Text, nullable=False)
    preference = db.Column(db.Text, nullable=False)  # 'none', 'immediate', or 'bulk'
    custom_rule = db.Column(db.Text, nullable=True)  # JSON for app-specific rules
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='notification_preferences')
    
    def __repr__(self):
        return f'<NotificationPreference {self.user_id}-{self.notification_type}>'


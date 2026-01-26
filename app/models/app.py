# IMPORTANT: Read instructions/architecture before making changes to this file
"""
App model for storing app registry information.
See instructions/architecture for development guidelines.
"""

from app import db
from datetime import datetime

class App(db.Model):
    """App registry model."""
    __tablename__ = 'apps'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    app_name = db.Column(db.Text, nullable=False, unique=True)  # URL-safe identifier
    app_display_name = db.Column(db.Text, nullable=False)
    app_description = db.Column(db.Text, nullable=True)
    app_url = db.Column(db.Text, nullable=True)
    github_url = db.Column(db.Text, nullable=True)
    app_owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    icon_path = db.Column(db.Text, nullable=True)  # Path to icon file in instance folder
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    feature_requests = db.relationship('FeatureRequest', backref='app', lazy='dynamic', foreign_keys='FeatureRequest.app_id')
    app_owner = db.relationship('User', foreign_keys=[app_owner_id], backref='owned_apps')
    
    def __repr__(self):
        return f'<App {self.app_name}>'


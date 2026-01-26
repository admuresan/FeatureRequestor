# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Configuration management for the application.
See instructions/architecture for development guidelines.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

def get_instance_path() -> Path:
    """Get the instance folder path."""
    return Path(__file__).parent.parent / 'instance'

def get_config_path() -> Path:
    """Get the path to config.json."""
    return get_instance_path() / 'config.json'

def load_config() -> Dict[str, Any]:
    """
    Load configuration from instance/config.json with defaults.
    
    Returns:
        Dictionary containing configuration values
    """
    config_path = get_config_path()
    defaults = {
        'confirmation_percentage': 80,
        'similar_request_max_results': 5,
        'similar_request_threshold': 0.6
    }
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                defaults.update(user_config)
        except (json.JSONDecodeError, IOError) as e:
            # If config file is invalid, use defaults and log error
            print(f"Warning: Could not load config.json: {e}. Using defaults.")
    
    return defaults

def save_config(config: Dict[str, Any]) -> bool:
    """
    Save configuration to instance/config.json.
    
    Args:
        config: Dictionary containing configuration values
    
    Returns:
        True if successful, False otherwise
    """
    config_path = get_config_path()
    instance_path = get_instance_path()
    instance_path.mkdir(exist_ok=True)
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except IOError as e:
        print(f"Error saving config.json: {e}")
        return False

def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get a specific configuration value.
    
    Args:
        key: Configuration key
        default: Default value if key not found
    
    Returns:
        Configuration value or default
    """
    config = load_config()
    return config.get(key, default)

def load_email_config() -> Dict[str, Any]:
    """Load email configuration from instance/email_config.json."""
    config_path = get_instance_path() / 'email_config.json'
    defaults = {
        'from_email_mask': 'noreply@feature-requestor.com',
        'smtp_host': '',
        'smtp_port': 587,
        'smtp_security': 'TLS',
        'smtp_username': '',
        'smtp_password': ''
    }
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                defaults.update(user_config)
        except (json.JSONDecodeError, IOError):
            pass
    
    return defaults

def save_email_config(config: Dict[str, Any]) -> bool:
    """Save email configuration to instance/email_config.json."""
    config_path = get_instance_path() / 'email_config.json'
    instance_path = get_instance_path()
    instance_path.mkdir(exist_ok=True)
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except IOError:
        return False

def load_email_templates() -> Dict[str, Any]:
    """Load email templates from instance/email_templates.json."""
    config_path = get_instance_path() / 'email_templates.json'
    defaults = {
        'email_verification': {
            'subject': 'Verify your email address',
            'body': '<p>Hello {user_name},</p><p>Please click the following link to verify your email address:</p><p><a href="{verification_link}">{verification_link}</a></p><p>If you did not create an account, please ignore this email.</p>'
        },
        'password_reset': {
            'subject': 'Reset your password',
            'body': '<p>Hello {user_name},</p><p>You requested to reset your password. Please click the following link to reset it:</p><p><a href="{reset_link}">{reset_link}</a></p><p>If you did not request a password reset, please ignore this email.</p><p>This link will expire in 24 hours.</p>'
        },
        'email_change_verification': {
            'subject': 'Verify your new email address',
            'body': '<p>Hello {user_name},</p><p>You requested to change your email address to {new_email}. Please click the following link to verify your new email address:</p><p><a href="{verification_link}">{verification_link}</a></p><p>If you did not request this change, please ignore this email.</p>'
        },
        'new_message': {
            'subject': 'New message on Feature Requestor',
            'body': '<p>Hello {user_name},</p><p>You have received a new message:</p><p>{message_content}</p><p><a href="{message_link}">View Message</a></p>'
        },
        'new_feature_request': {
            'subject': 'New feature request: {feature_request_title}',
            'body': '<p>Hello {user_name},</p><p>A new feature request has been created for {app_name}:</p><p><strong>{feature_request_title}</strong></p><p>{feature_request_description}</p><p><a href="{feature_request_link}">View Feature Request</a></p>'
        },
        'feature_request_status_change': {
            'subject': 'Feature request status changed: {feature_request_title}',
            'body': '<p>Hello {user_name},</p><p>The status of the feature request "{feature_request_title}" for {app_name} has been changed to: <strong>{new_status}</strong></p><p><a href="{feature_request_link}">View Feature Request</a></p>'
        },
        'new_comment': {
            'subject': 'New comment on feature request: {feature_request_title}',
            'body': '<p>Hello {user_name},</p><p>A new comment has been added to the feature request "{feature_request_title}":</p><p>{comment_content}</p><p><a href="{feature_request_link}">View Feature Request</a></p>'
        },
        'payment_received': {
            'subject': 'Payment received for feature request: {feature_request_title}',
            'body': '<p>Hello {user_name},</p><p>You have received a payment of {amount} for the feature request "{feature_request_title}" on {app_name}.</p><p><a href="{feature_request_link}">View Feature Request</a></p>'
        }
    }
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                user_templates = json.load(f)
                # Merge user templates with defaults (user templates override defaults)
                defaults.update(user_templates)
        except (json.JSONDecodeError, IOError):
            pass
    
    return defaults

def save_email_templates(templates: Dict[str, Any]) -> bool:
    """Save email templates to instance/email_templates.json."""
    config_path = get_instance_path() / 'email_templates.json'
    instance_path = get_instance_path()
    instance_path.mkdir(exist_ok=True)
    
    try:
        with open(config_path, 'w') as f:
            json.dump(templates, f, indent=2)
        return True
    except IOError:
        return False

def load_stripe_config() -> Dict[str, Any]:
    """Load Stripe configuration from instance/stripe_config.json."""
    config_path = get_instance_path() / 'stripe_config.json'
    defaults = {
        'stripe_public_key': '',
        'stripe_secret_key': '',
        'stripe_client_id': '',
        'stripe_webhook_secret': ''
    }
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                defaults.update(user_config)
        except (json.JSONDecodeError, IOError):
            pass
    
    return defaults

def save_stripe_config(config: Dict[str, Any]) -> bool:
    """Save Stripe configuration to instance/stripe_config.json."""
    config_path = get_instance_path() / 'stripe_config.json'
    instance_path = get_instance_path()
    instance_path.mkdir(exist_ok=True)
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except IOError:
        return False

def get_stripe_key(key_name: str) -> str:
    """
    Get a Stripe API key, checking environment variables first, then config file.
    Environment variables take precedence for security.
    
    Args:
        key_name: One of 'stripe_public_key', 'stripe_secret_key', 'stripe_client_id', 'stripe_webhook_secret'
    
    Returns:
        The API key value, or empty string if not found
    """
    # Check environment variable first (takes precedence)
    env_key = key_name.upper()
    env_value = os.environ.get(env_key, '')
    if env_value:
        return env_value
    
    # Fall back to config file
    config = load_stripe_config()
    return config.get(key_name, '')

